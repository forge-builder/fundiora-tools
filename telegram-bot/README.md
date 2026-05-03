# Fundiora Telegram Alert Bot

A Telegram bot that serves FUND holders with real-time price alerts, whale activity tracking, and holder stats — running 24/7 on the Mac Mini.

## Features

- **Live Price** — `/price` shows current FUND price, market cap, liquidity, 24h volume
- **Price Alerts** — `/alert above [price]` or `/alert below [price]` — get notified when FUND hits your target
- **Whale Alerts** — Auto-posts to your chat when >1M FUND transfers occur on-chain
- **Holder Count** — `/holders` shows current holder count
- **24/7 Operation** — Runs as a background service on the Mac Mini

## Quick Start

### 1. Create a Telegram Bot

1. Open Telegram and chat with **@BotFather**
2. Send `/newbot`
3. Follow the prompts — give it a name and username
4. Copy the **bot token** BotFather gives you (looks like `123456789:ABCdef...`)

### 2. Set Up the Bot

```bash
cd ~/fundiora-tools/telegram-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env with your bot token
cp .env.example .env
nano .env   # Replace with your actual TELEGRAM_BOT_TOKEN

# Test it
python alert_bot.py
```

### 3. Get Your Chat ID

1. Open Telegram and send `/start` to your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789,...` — that's your **chat_id**

### 4. Run It

```bash
source venv/bin/activate
python alert_bot.py
```

### 5. Run 24/7 (Systemd)

```bash
# Create the service file
sudo nano /etc/systemd/system/fundiora-bot.service
```

Paste this (adjust paths):

```ini
[Unit]
Description=Fundiora Telegram Alert Bot
After=network.target

[Service]
Type=simple
User=roger
WorkingDirectory=/Users/roger/fundiora-tools/telegram-bot
ExecStart=/Users/roger/fundiora-tools/telegram-bot/venv/bin/python alert_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fundiora-bot
sudo systemctl start fundiora-bot
sudo systemctl status fundiora-bot
```

## Commands

| Command | Description |
|---------|-------------|
| `/price` | Live FUND price, MCAP, liquidity, 24h volume |
| `/alert above 0.00003` | Alert when price rises above target |
| `/alert below 0.00002` | Alert when price drops below target |
| `/alert list` | Show your active alerts |
| `/alert delete 1` | Delete an alert by number |
| `/holders` | Current holder count |
| `/help` | Show all commands |

## Whale Alerts

The bot monitors the Base blockchain for FUND transfers >1M tokens. When a whale move happens, it posts an alert to all chats that have interacted with the bot.

Whale threshold: **1,000,000 FUND** (configurable in `alert_bot.py`)

## Data Sources

- **Price:** GeckoTerminal API (free, no key)
- **Holders:** BaseScan API (free tier)
- **Transfers:** Base Public RPC (free, no key)
- **Contract:** `0xa02d9a9a5f5453463aa4855f62e47d9cc27086d9` on Base

## Troubleshooting

**"Unable to fetch price data"**
→ GeckoTerminal might be rate-limiting. Wait 30 seconds and try again.

**Bot not responding**
→ Check the bot token is correct in `.env`
→ Make sure you ran `source venv/bin/activate`
→ Check logs for errors

**Whale alerts not working**
→ The bot needs to have been started at least once to register chat IDs
→ Transfers are logged to `transfers.log` to avoid duplicate alerts

## Architecture

```
alert_bot.py       — Main bot (python-telegram-bot v20 async)
price_fetcher.py   — GeckoTerminal + BaseScan API calls (embedded in alert_bot.py)
alert_store.json   — Persistent alert storage (auto-created)
transfers.log     — Processed whale transfers (avoids duplicates)
.env              — Bot token (create from .env.example)
```

## Adding the Bot to a Channel

1. Add the bot as an admin to your Telegram channel
2. Use the channel's chat ID (negative number, e.g., `-1001234567890`)
3. The bot will post whale alerts to all registered chats

## Questions?

Reach out via the Fundiora community channels.
