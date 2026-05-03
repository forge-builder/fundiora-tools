# Fundiora Telegram Alert Bot — SPEC

## Overview
A Telegram bot that serves FUND holders with real-time alerts, price updates, and whale activity tracking. Operates 24/7 on the Mac Mini.

## What It Does
1. **Live Price** — `/price` shows current FUND price, market cap, liquidity, 24h volume
2. **Price Alerts** — `/alert [above|below] [price]` sets personal price threshold alerts
3. **Holder Count** — `/holders` shows current holder count from on-chain data
4. **Whale Alerts** — Auto-posts to channel when a transfer >1M FUND occurs
5. **Daily Summary** — Optional daily recap of price movement and holder changes

## Architecture
```
alert_bot.py        — Main bot (python-telegram-bot v20+)
price_fetcher.py    — GeckoTerminal + BaseScan API calls
alert_store.json    — Persistent alert storage (per chat_id)
transfers.log      — Track processed transfer hashes (avoid duplicate alerts)
requirements.txt    — Dependencies
.env.example        — Environment template
README.md           — Setup guide
```

## Tech Stack
- Python 3.11+
- python-telegram-bot v20 (async)
- requests (API calls)
- Base RPC: https://base.publicnode.com (free, no key)
- GeckoTerminal API: https://geckoterminal.com/api/v2/...

## FUND Contract
- Address: `0xa02d9a9a5f5453463aa4855f62e47d9cc27086d9`
- Network: Base (chainId: 8453)
- Pool: `0xdb5df2ee10219015b207b055828076d9366d7fdb` (Uniswap V3)

## Bot Token
Get from @BotFather on Telegram. Put in `.env` as `TELEGRAM_BOT_TOKEN`.

## Deployment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your TELEGRAM_BOT_TOKEN to .env
python alert_bot.py
```

Run as systemd service for 24/7 operation.
