#!/usr/bin/env python3
"""Jev News Sentiment Bot - CLI entry point.

Usage:
    python run.py fetch     # Fetch news from RSS feeds
    python run.py judge     # Fetch + judge articles via Jev
    python run.py monitor   # Continuous fetch + judge loop
    python run.py stats     # Show last aggregated sentiment
"""
import sys
import os
import time
import json
import yaml
from datetime import datetime, timezone

# Load .env
from dotenv import load_dotenv
load_dotenv()

from news_fetcher import fetch_all, Article
from sentiment import judge_articles, aggregate_sentiment, print_sentiment_report
from logger import SentimentLogger


def load_config() -> dict:
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def cmd_fetch(config: dict, sentiment_logger: SentimentLogger):
    """Fetch articles from all RSS feeds."""
    print("Fetching crypto news...")
    articles = fetch_all(config["feeds"])
    print(f"\nTotal: {len(articles)} articles fetched")

    # Show top 10
    for i, a in enumerate(articles[:10]):
        print(f"  {i+1}. [{a.source}] {a.title[:80]}")

    # Save fetched articles to file
    os.makedirs("data", exist_ok=True)
    with open("data/fetched_articles.json", "w") as f:
        json.dump([a.to_dict() for a in articles], f, indent=2, default=str)
    print(f"\nSaved to data/fetched_articles.json")

    for feed_cfg in config["feeds"]:
        sentiment_logger.log_fetch(feed_cfg["name"], len(articles))

    return articles


def cmd_judge(config: dict, sentiment_logger: SentimentLogger):
    """Fetch and judge articles."""
    articles = cmd_fetch(config, sentiment_logger)

    if not articles:
        print("No articles to judge.")
        return

    max_articles = config.get("sentiment", {}).get("max_articles", 20)
    judged = judge_articles(articles, sentiment_logger, max_articles=max_articles)

    if judged:
        decay_hours = config.get("sentiment", {}).get("decay_hours", 24)
        aggregated = aggregate_sentiment(judged, decay_hours=decay_hours)
        print_sentiment_report(aggregated)

        # Save results
        os.makedirs("data", exist_ok=True)
        with open("data/sentiment_report.json", "w") as f:
            json.dump(aggregated, f, indent=2, default=str)
        print("Report saved to data/sentiment_report.json")

        for asset, data in aggregated.items():
            sentiment_logger.log_aggregate(
                asset, data["score"], data["count"], data["bias"]
            )
    else:
        print("No articles were successfully judged.")


def cmd_monitor(config: dict, sentiment_logger: SentimentLogger):
    """Continuous monitoring loop."""
    interval = config.get("sentiment", {}).get("update_interval_seconds", 300)
    print(f"Starting monitor (interval: {interval}s, Ctrl+C to stop)")

    while True:
        try:
            print(f"\n--- Cycle at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')} ---")
            cmd_judge(config, sentiment_logger)
            print(f"\nNext cycle in {interval}s...")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break


def cmd_stats(config: dict):
    """Show last saved sentiment report."""
    try:
        with open("data/sentiment_report.json") as f:
            aggregated = json.load(f)
        print_sentiment_report(aggregated)
    except FileNotFoundError:
        print("No sentiment report found. Run 'python run.py judge' first.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    config = load_config()
    sentiment_logger = SentimentLogger(
        config.get("logging", {}).get("file", "data/sentiment_log.jsonl")
    )

    if command == "fetch":
        cmd_fetch(config, sentiment_logger)
    elif command == "judge":
        cmd_judge(config, sentiment_logger)
    elif command == "monitor":
        cmd_monitor(config, sentiment_logger)
    elif command == "stats":
        cmd_stats(config)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
