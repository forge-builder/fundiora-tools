#!/usr/bin/env python3
"""
Fundiora X Content Generator
Generates content drafts for @saint_ezziee999's X posts.
Run with: python content_generator.py
"""

import os
import json
import random
from datetime import datetime
from pathlib import Path
import requests

# ─── CONFIG ───────────────────────────────────────────────────────────────────

POOL_URL = "https://geckoterminal.com/api/v2/networks/base/pools/0xdb5df2ee10219015b207b055828076d9366d7fdb"
OUTPUT_FILE = Path(__file__).parent / "content_drafts.json"
HISTORY_FILE = Path(__file__).parent / "posted_history.json"

# ─── PRICE FETCHING ───────────────────────────────────────────────────────────

def get_price_data() -> dict:
    try:
        resp = requests.get(POOL_URL, timeout=10)
        data = resp.json()
        attrs = data["data"]["attributes"]
        base_price = float(attrs.get("base_token_price_usd", 0))
        quote_price = float(attrs.get("quote_token_price_usd", 0))

        if base_price == 0 and quote_price > 0:
            price = 1.0 / quote_price
        else:
            price = base_price

        mcap = price * 900_000_000
        liq = float(attrs.get("reserve_in_usd", 0))
        vol = float(attrs.get("volume_usd", {}).get("h24", 0))
        change = float(attrs.get("price_change_24h", 0))

        return {
            "price": price,
            "mcap": mcap,
            "liq": liq,
            "vol": vol,
            "change_24h": change,
            "updated": datetime.now().isoformat()
        }
    except Exception as e:
        return {}


def format_price(price: float) -> str:
    if price < 0.00001:
        return f"${price:.8f}"
    elif price < 0.001:
        return f"${price:.6f}"
    return f"${price:.4f}"


# ─── CONTENT TEMPLATES ────────────────────────────────────────────────────────

class ContentTemplates:
    """Collection of X post templates for Fundiora."""

    @staticmethod
    def price_update(price: float, change: float, mcap: float) -> str:
        emoji = "📈" if change >= 0 else "📉"
        sign = "+" if change >= 0 else ""
        return (
            f"$FUND {emoji}\n"
            f"Price: {format_price(price)}\n"
            f"24h: {sign}{change:.1f}%\n"
            f"MCap: ${mcap:,.0f}\n\n"
            f"#Fundiora #Base #Crypto"
        )

    @staticmethod
    def whale_alert(amount_str: str, tx_short: str) -> str:
        return (
            f"🐋 Whale activity on $FUND\n"
            f"{amount_str} tokens moved\n\n"
            f"This is what community-driven crypto looks like.\n"
            f"Not a pepe. Not a meme. A movement.\n\n"
            f"#Fundiora #Base"
        )

    @staticmethod
    def utility_reminder() -> str:
        return (
            f"$FUND utility check:\n\n"
            f"✅ 5% yearly yield for 100K+ holders\n"
            f"✅ 10-year LP lock\n"
            f"✅ OpenZeppelin verified contract\n"
            f"✅ 169 holders and growing\n\n"
            f"What are you waiting for?\n\n"
            f"#Fundiora #Base #Hold"
        )

    @staticmethod
    def community_story() -> str:
        stories = [
            "We didn't launch with a bang. We built with a plan. 10 months in, 169 holders, locked liquidity, and a yield program that actually pays out.",
            "Most tokens promise. Fundiora locks. The LP is verified on-chain. The contract is public. The yield program is real.",
            "Crypto doesn't have to be a rug pull. It can be a community. It can be transparent. It can be Fundiora.",
            "Small caps get dismissed. But that's exactly where the community is realest. No bots. No wash trading. Just holders who believe.",
        ]
        return (
            random.choice(stories) + "\n\n"
            f"#Fundiora #Base #Community"
        )

    @staticmethod
    def agent_tease() -> str:
        return (
            f"AI agents for crypto communities.\n\n"
            f"Not a chatbot. Not a hype machine.\n"
            f"Real infrastructure. Real utility.\n\n"
            f"$FUND holders get first access.\n\n"
            f"#Fundiora #AI #Agents"
        )

    @staticmethod
    def educational() -> str:
        topics = [
            ("Why small caps on Base are underrated", "Base is EVM-compatible, has low gas, and is backed by Coinbase. The projects there are early. $FUND is one of them."),
            ("What makes a token worth holding", "Not the chart. Not the influencer. The contract, the liquidity, and whether people actually use it."),
            ("Why Fundiora chose Base", "Fast, cheap, Coinbase-backed. And a community that actually believes in the product."),
        ]
        topic, body = random.choice(topics)
        return (
            f"🧠 {topic}\n\n"
            f"{body}\n\n"
            f"#Crypto #Base #Fundiora"
        )

    @staticmethod
    def question_post() -> str:
        questions = [
            "What would you build if you had a token that pays you to hold it?",
            "Who else is building on Base this year? 👇",
            "What's more important: price or community?",
            "What utility would make you hold a token for 5 years?",
        ]
        return (
            f"{random.choice(questions)}\n\n"
            f"#Fundiora #Crypto"
        )

    @staticmethod
    def hold_reminder() -> str:
        return (
            f"Hold.\n\n"
            f"Not financial advice.\n"
            f"But also: the contract is clean, the LP is locked, the yield is real.\n"
            f"Build your position.\n\n"
            f"#Fundiora #Hold"
        )

    @staticmethod
    def weekly_recap() -> str:
        return (
            f"📊 Weekly $FUND Recap\n\n"
            f"Built on Base. 169 holders. 5% yearly yield.\n"
            f"No hype. No promises.\n"
            f"Just a community that shows up.\n\n"
            f"#Fundiora #Base"
        )

    @staticmethod
    def bullish_micro() -> str:
        return (
            f"Micro cap season is coming.\n\n"
            f"The tokens that actually built something will be the ones that survive it.\n"
            f"$FUND has: contract, community, yield.\n\n"
            f"👀\n\n"
            f"#Fundiora #Base #MicroCap"
        )


# ─── GENERATOR ───────────────────────────────────────────────────────────────

def generate_content_batch(n: int = 5) -> list[dict]:
    """Generate n content drafts."""
    templates = ContentTemplates()
    price_data = get_price_data()
    posts = []

    # Mix of content types
    generators = [
        ("price", templates.price_update, 2),
        ("whale", templates.whale_alert, 0),
        ("utility", templates.utility_reminder, 1),
        ("story", templates.community_story, 2),
        ("agent", templates.agent_tease, 1),
        ("educational", templates.educational, 1),
        ("question", templates.question_post, 1),
        ("hold", templates.hold_reminder, 1),
        ("recap", templates.weekly_recap, 0),
        ("bullish", templates.bullish_micro, 1),
    ]

    # Always include at least one price update if we have data
    if price_data.get("price"):
        posts.append({
            "type": "price",
            "draft": templates.price_update(
                price_data["price"],
                price_data["change_24h"],
                price_data["mcap"]
            ),
            "price_data": price_data,
            "char_count": len(templates.price_update(
                price_data["price"],
                price_data["change_24h"],
                price_data["mcap"]
            ))
        })

    # Fill remaining slots (price_update is handled separately above)
    pool = []
    for name, fn, weight in generators:
        if name != "price":  # price is handled separately with live data
            pool.extend([fn] * weight)

    random.shuffle(pool)
    for gen_fn in pool[:n-1]:
        posts.append({
            "type": "template",
            "draft": gen_fn(),
            "char_count": len(gen_fn())
        })

    return posts


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print(f"Generating content drafts at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    posts = generate_content_batch(5)

    # Save to file
    output = {
        "generated_at": datetime.now().isoformat(),
        "posts": posts
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nGenerated {len(posts)} drafts → {OUTPUT_FILE}\n")
    for i, post in enumerate(posts, 1):
        post_type = post.get("type", "unknown")
        draft = post["draft"]
        chars = post["char_count"]
        over = "⚠️ OVER 280" if chars > 280 else "✓"
        print(f"[{i}] ({post_type}) {chars} chars {over}")
        print(f"    {draft[:80]}...")
        print()

    print("Edit content_drafts.json to customize, then post manually or via xurl skill.")


if __name__ == "__main__":
    main()
