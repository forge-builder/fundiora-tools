#!/usr/bin/env python3
"""
Fundiora Alert Bot — Telegram Bot for FUND Holders
Run with: python alert_bot.py
Requires: TELEGRAM_BOT_TOKEN in .env or environment
"""

import os
import json
import math
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

BOT_NAME = "Fundiora Alert Bot"
CONTRACT = "0xa02d9a9a5f5453463aa4855f62e47d9cc27086d9"
POOL_ADDRESS = "0xdb5df2ee10219015b207b055828076d9366d7fdb"
BASE_RPC = "https://base.publicnode.com"
GECKO_URL = f"https://geckoterminal.com/api/v2/networks/base/pools/{POOL_ADDRESS}"
BASESCAN_URL = f"https://api.basescan.org/api?module=token&action=tokenholdercount&contractaddress={CONTRACT}"

ALERT_FILE = Path(__file__).parent / "alert_store.json"
WHALE_THRESHOLD = 1_000_000  # 1M FUND — triggers whale alert
WHALE_LOG = Path(__file__).parent / "transfers.log"

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
log = logging.getLogger(BOT_NAME)

# ─── STATE ────────────────────────────────────────────────────────────────────

price_cache = {"price": None, "mcap": None, "liq": None, "vol": None, "updated": None}
holders_cache = {"count": None, "updated": None}
last_block = None

# ─── PRICE FETCHING ───────────────────────────────────────────────────────────

def get_price_data() -> dict:
    """Fetch live price data from GeckoTerminal API."""
    global price_cache
    try:
        resp = requests.get(GECKO_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        attributes = data["data"]["attributes"]
        base_price = float(attributes.get("base_token_price_usd", 0))
        quote_price = float(attributes.get("quote_token_price_usd", 0))
        # Derive FUND price from quote if base is zero
        if base_price == 0 and quote_price > 0:
            price = 1.0 / quote_price if quote_price else 0
        else:
            price = base_price

        # GeckoTerminal returns price in USD
        price_usd = price

        # Market cap = price * 900M circulating supply
        mcap = price_usd * 900_000_000

        # Liquidity in USD
        liq = float(attributes.get("reserve_in_usd", 0))

        # 24h volume
        vol = float(attributes.get("volume_usd", {}).get("h24", 0))

        # Price change 24h
        price_change = attributes.get("price_change_24h", 0)

        price_cache = {
            "price": price_usd,
            "mcap": mcap,
            "liq": liq,
            "vol": vol,
            "price_change_24h": price_change,
            "updated": datetime.now().isoformat()
        }
        return price_cache

    except Exception as e:
        log.warning(f"Price fetch failed: {e}")
        return price_cache if price_cache["price"] else {}


def get_holders() -> int:
    """Fetch holder count from BaseScan API (free tier, no key for reads)."""
    global holders_cache
    try:
        # BaseScan free API for holder count
        url = f"https://api.basescan.org/api"
        params = {
            "module": "token",
            "action": "tokenholdercount",
            "contractaddress": CONTRACT,
            "apikey": ""  # BaseScan allows ~3-5 calls/sec without key for reads
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        count = int(data["result"])
        holders_cache = {"count": count, "updated": datetime.now().isoformat()}
        return count
    except Exception as e:
        log.warning(f"Holders fetch failed: {e}")
        return holders_cache.get("count") or 0


# ─── WHALE DETECTION ─────────────────────────────────────────────────────────

def get_recent_transfers(from_block: int = None) -> list:
    """Get recent large FUND transfers via Base RPC."""
    try:
        # Get current block
        block_resp = requests.post(BASE_RPC, json={
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }, timeout=10)
        current_block = int(block_resp.json()["result"], 16)

        # Fetch Transfer events from the last 100 blocks
        from_block = from_block or current_block - 100

        # Transfer(event) sig: Transfer(address,address,uint256)
        # Topic0 = keccak("Transfer(address,address,uint256)")
        topic0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df35b9dc"

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(from_block),
                "toBlock": hex(current_block),
                "address": CONTRACT,
                "topics": [topic0],
                "limit": 100
            }],
            "id": 1
        }
        resp = requests.post(BASE_RPC, json=payload, timeout=15)
        logs = resp.json().get("result", [])
        return logs, current_block
    except Exception as e:
        log.warning(f"Transfer fetch failed: {e}")
        return [], from_block


def is_new_transfer(tx_hash: str) -> bool:
    """Check if we've already processed this transfer."""
    if not WHALE_LOG.exists():
        return True
    with open(WHALE_LOG) as f:
        return tx_hash not in f.read()


def mark_processed(tx_hash: str):
    """Log processed transfer to avoid duplicates."""
    with open(WHALE_LOG, "a") as f:
        f.write(tx_hash + "\n")


def format_amount(raw_amount: int) -> str:
    """Format FUND amount in human-readable form."""
    if raw_amount >= 1_000_000:
        return f"{raw_amount / 1_000_000:.1f}M"
    elif raw_amount >= 1_000:
        return f"{raw_amount / 1_000:.0f}K"
    return str(raw_amount)


def check_whale_alerts(app: Application):
    """Background job: check for large transfers and post alerts."""
    global last_block

    logs, current_block = get_recent_transfers(last_block or None)
    last_block = current_block

    for log_entry in logs:
        try:
            tx_hash = log_entry.get("transactionHash", "")
            topics = log_entry.get("topics", [])

            if len(topics) < 4:
                continue

            # Decode amount from data (third topic is amount for Transfer)
            # data field contains the uint256 amount for Transfer(address from, address to, uint256 amount)
            data = log_entry.get("data", "0x0")
            amount = int(data, 16) if data != "0x0" else 0

            if amount >= WHALE_THRESHOLD:
                if is_new_transfer(tx_hash):
                    mark_processed(tx_hash)
                    # Build alert message
                    amount_str = format_amount(amount)
                    block = log_entry.get("blockNumber", "?")
                    msg = (
                        f"🐋 <b>WHALE ALERT</b>\n"
                        f"<code>{amount_str} $FUND</code>\n"
                        f"Block: <code>{block}</code>\n"
                        f"Tx: <code>{tx_hash[:10]}...{tx_hash[-6:]}</code>"
                    )
                    # Send to all registered chats
                    for chat_id in load_alerts().keys():
                        try:
                            app.bot.send_message(
                                chat_id=int(chat_id),
                                text=msg,
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
        except Exception as e:
            log.warning(f"Whale alert processing error: {e}")
            continue


# ─── ALERT STORE ──────────────────────────────────────────────────────────────

def load_alerts() -> dict:
    """Load alert store from disk."""
    if not ALERT_FILE.exists():
        return {}
    try:
        with open(ALERT_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_alerts(alerts: dict):
    """Save alert store to disk."""
    with open(ALERT_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def format_price(price: float) -> str:
    """Format price in appropriate precision."""
    if price < 0.00001:
        return f"${price:.8f}"
    elif price < 0.001:
        return f"${price:.6f}"
    elif price < 1:
        return f"${price:.4f}"
    return f"${price:.2f}"


# ─── COMMAND HANDLERS ────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    alerts = load_alerts()
    if chat_id not in alerts:
        alerts[chat_id] = {"alerts": [], "enabled": True}
        save_alerts(alerts)

    keyboard = [
        [InlineKeyboardButton("📊 Price", callback_data="btn_price")],
        [InlineKeyboardButton("🔔 Set Alert", callback_data="btn_alert")],
        [InlineKeyboardButton("👥 Holders", callback_data="btn_holders")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="btn_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"<b>Welcome to the Fundiora Alert Bot</b>\n\n"
        f"Stay updated on $FUND — real-time price, whale alerts, and holder stats.\n\n"
        f"<i>Built for the Fundiora community on Base.</i>",
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = get_price_data()
    if not data.get("price"):
        await update.message.reply_text("⚠️ Unable to fetch price data. Try again shortly.")
        return

    price = data["price"]
    mcap = data.get("mcap", 0)
    liq = data.get("liq", 0)
    vol = data.get("vol", 0)
    change = data.get("price_change_24h", 0)

    change_emoji = "🟢" if change >= 0 else "🔴"
    change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

    await update.message.reply_text(
        f"<b>$FUND — Live Price</b>\n\n"
        f"<code>{format_price(price)}</code>\n"
        f"{change_emoji} {change_str} (24h)\n\n"
        f"<b>Market Cap:</b> ${mcap:,.0f}\n"
        f"<b>Liquidity:</b> ${liq:,.0f}\n"
        f"<b>24h Volume:</b> ${vol:,.2f}\n\n"
        f"<i>Updated: {data['updated'][:19]}</i>",
        parse_mode="HTML"
    )


async def cmd_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    args = ctx.args

    alerts = load_alerts()
    if chat_id not in alerts:
        alerts[chat_id] = {"alerts": [], "enabled": True}

    if not args:
        # Show current alerts
        user_alerts = alerts[chat_id].get("alerts", [])
        if not user_alerts:
            text = "📭 <b>No alerts set.</b>\n\nUsage: /alert above 0.00003\n       /alert below 0.00002\n       /alert list\n       /alert delete 1"
        else:
            lines = []
            for i, a in enumerate(user_alerts, 1):
                lines.append(f"{i}. {a['direction'].upper()} {format_price(a['threshold'])}")
            text = "🔔 <b>Your alerts:</b>\n\n" + "\n".join(lines) + "\n\nDelete: /alert delete [number]"
        await update.message.reply_text(text, parse_mode="HTML")
        return

    subcmd = args[0].lower()

    if subcmd == "list":
        user_alerts = alerts[chat_id].get("alerts", [])
        if not user_alerts:
            await update.message.reply_text("📭 No alerts set.")
            return
        lines = [f"{i}. {a['direction'].upper()} {format_price(a['threshold'])}" for i, a in enumerate(user_alerts, 1)]
        await update.message.reply_text("🔔 <b>Your alerts:</b>\n\n" + "\n".join(lines), parse_mode="HTML")
        return

    if subcmd == "delete":
        try:
            idx = int(args[1]) - 1
            deleted = alerts[chat_id]["alerts"].pop(idx)
            save_alerts(alerts)
            await update.message.reply_text(f"✅ Deleted alert: {deleted['direction'].upper()} {format_price(deleted['threshold'])}")
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Invalid alert number. Use /alert list to see numbers.")
        return

    if subcmd in ("above", "below"):
        try:
            threshold = float(args[1])
            alert = {"direction": subcmd, "threshold": threshold, "triggered": False}
            alerts[chat_id].setdefault("alerts", []).append(alert)
            save_alerts(alerts)
            await update.message.reply_text(
                f"✅ <b>Alert set!</b>\n"
                f"I'll notify you when FUND goes {subcmd.upper()} {format_price(threshold)}",
                parse_mode="HTML"
            )
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Usage: /alert above 0.00003")
        return

    await update.message.reply_text("❌ Unknown command. Try: /alert above 0.00003, /alert below 0.00002, /alert list, /alert delete 1")


async def cmd_holders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    count = get_holders()
    updated = holders_cache.get("updated", "unknown")[:19] if holders_cache.get("updated") else "unknown"
    await update.message.reply_text(
        f"<b>FUND Holder Count</b>\n\n"
        f"<code>{count:,}</code> holders\n\n"
        f"<i>Updated: {updated}</i>",
        parse_mode="HTML"
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Fundiora Alert Bot — Commands</b>\n\n"
        "<code>/price</code> — Live FUND price, MCAP, liquidity\n"
        "<code>/alert above [price]</code> — Alert when price rises above\n"
        "<code>/alert below [price]</code> — Alert when price drops below\n"
        "<code>/alert list</code> — Show your active alerts\n"
        "<code>/alert delete [n]</code> — Delete an alert\n"
        "<code>/holders</code> — Current holder count\n"
        "<code>/help</code> — This message\n\n"
        "<b>Whale Alerts</b> — Auto-posted when >1M FUND transfers\n\n"
        "<i>Data from GeckoTerminal + Base RPC · Updated in real-time</i>",
        parse_mode="HTML"
    )


# ─── CALLBACK HANDLERS ───────────────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_price":
        data = get_price_data()
        if data.get("price"):
            price = data["price"]
            mcap = data.get("mcap", 0)
            liq = data.get("liq", 0)
            vol = data.get("vol", 0)
            change = data.get("price_change_24h", 0)
            change_emoji = "🟢" if change >= 0 else "🔴"
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
            text = (f"<b>$FUND — Live Price</b>\n\n"
                    f"<code>{format_price(price)}</code>\n{change_emoji} {change_str} (24h)\n\n"
                    f"<b>Market Cap:</b> ${mcap:,.0f}\n"
                    f"<b>Liquidity:</b> ${liq:,.0f}\n"
                    f"<b>24h Volume:</b> ${vol:,.2f}")
        else:
            text = "⚠️ Unable to fetch price data."
        await query.edit_message_text(text, parse_mode="HTML")

    elif query.data == "btn_alert":
        await query.edit_message_text(
            "🔔 <b>Set a Price Alert</b>\n\n"
            "Send a message like:\n"
            "<code>/alert above 0.00003</code>\n"
            "<code>/alert below 0.00002</code>\n\n"
            "I'll notify you when FUND hits that price!",
            parse_mode="HTML"
        )

    elif query.data == "btn_holders":
        count = get_holders()
        await query.edit_message_text(
            f"<b>FUND Holder Count</b>\n\n"
            f"<code>{count:,}</code> holders",
            parse_mode="HTML"
        )

    elif query.data == "btn_help":
        await cmd_help(update, ctx)


# ─── WHALE CHECK JOB ─────────────────────────────────────────────────────────

async def whale_check_job(app: Application):
    """Runs every 60 seconds via Application.post_update."""
    check_whale_alerts(app)


async def post_init(app: Application):
    """Runs once after bot startup."""
    log.info("Fundiora Alert Bot started!")
    # Run whale check every 60 seconds
    app.job_queue.run_repeating(whale_check_job, interval=60, first=10)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        # Try to load from .env file
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            for line in env_file.read().splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set.")
        print("Create a .env file with: TELEGRAM_BOT_TOKEN=your_token_here")
        print("Or export TELEGRAM_BOT_TOKEN=your_token_here")
        print("\nGet a token from @BotFather on Telegram.")
        return

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("holders", cmd_holders))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(callback_handler))

    log.info(f"Starting {BOT_NAME}...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
