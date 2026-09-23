"""JSONL logger for sentiment data."""
import json
import os
from datetime import datetime, timezone


class SentimentLogger:
    def __init__(self, filepath: str = "data/sentiment_log.jsonl"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    def log(self, event_type: str, data: dict):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            **data,
        }
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_fetch(self, source: str, count: int):
        self.log("fetch", {"source": source, "articles_fetched": count})

    def log_judge(self, article_url: str, asset: str, sentiment: str,
                  material: bool, regulatory: bool):
        self.log("judge", {
            "url": article_url,
            "asset": asset,
            "sentiment": sentiment,
            "material": material,
            "regulatory_risk": regulatory,
        })

    def log_aggregate(self, asset: str, score: float, count: int, bias: str):
        self.log("aggregate", {
            "asset": asset,
            "sentiment_score": score,
            "article_count": count,
            "bias": bias,
        })
