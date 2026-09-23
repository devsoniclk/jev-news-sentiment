"""Sentiment aggregation per asset with time decay."""
import math
from datetime import datetime, timezone, timedelta
from typing import Optional
from news_fetcher import Article
import jev_client
import logger as log_module


SENTIMENT_LABELS = {
    1.0: "very-negative",
    2.0: "negative",
    3.0: "neutral",
    4.0: "positive",
    5.0: "very-positive",
}


def judge_articles(articles: list[Article], sentiment_logger: log_module.SentimentLogger,
                   max_articles: int = 20) -> list[Article]:
    """Send articles to Jev for judgment. Limits to max_articles."""
    judged = []
    to_judge = articles[:max_articles]
    print(f"\nJudging {len(to_judge)} articles via Jev...")

    for i, article in enumerate(to_judge):
        print(f"  [{i+1}/{len(to_judge)}] {article.title[:70]}...")
        result = jev_client.judge_article(article.title, article.summary)

        if result:
            article.asset = result.get("asset", "other")
            article.sentiment = result.get("sentiment", "neutral")
            article.sentiment_score = result.get("sentiment_score", 3.0)
            article.material = result.get("material", False)
            article.regulatory = result.get("regulatory", False)

            sentiment_logger.log_judge(
                article.url, article.asset, article.sentiment,
                article.material, article.regulatory,
            )
            print(f"    -> {article.asset} | {article.sentiment} ({article.sentiment_score}) "
                  f"| material={article.material} | regulatory={article.regulatory}")
            judged.append(article)
        else:
            print(f"    -> FAILED")

    return judged


def aggregate_sentiment(articles: list[Article], decay_hours: float = 24.0,
                        now: Optional[datetime] = None) -> dict:
    """Aggregate sentiment per asset with exponential time decay.

    Returns dict: {asset: {score, count, bias, avg_score, material_count, regulatory_count}}
    """
    now = now or datetime.now(timezone.utc)
    tau = decay_hours / math.log(2)  # half-life = decay_hours

    per_asset = {}
    for article in articles:
        if not article.asset or article.sentiment_score is None:
            continue

        # Time decay weight
        age_hours = (now - article.published).total_seconds() / 3600
        weight = math.exp(-age_hours / tau)

        asset = article.asset
        if asset not in per_asset:
            per_asset[asset] = {
                "weighted_sum": 0.0,
                "weight_total": 0.0,
                "count": 0,
                "material_count": 0,
                "regulatory_count": 0,
                "raw_scores": [],
            }

        bucket = per_asset[asset]
        bucket["weighted_sum"] += article.sentiment_score * weight
        bucket["weight_total"] += weight
        bucket["count"] += 1
        bucket["raw_scores"].append(article.sentiment_score)
        if article.material:
            bucket["material_count"] += 1
        if article.regulatory:
            bucket["regulatory_count"] += 1

    # Compute final scores and bias
    results = {}
    for asset, data in per_asset.items():
        if data["weight_total"] > 0:
            avg_score = data["weighted_sum"] / data["weight_total"]
        else:
            avg_score = 3.0

        # Determine trading bias
        if avg_score >= 4.0:
            bias = "BULLISH"
        elif avg_score >= 3.5:
            bias = "LEAN_BULLISH"
        elif avg_score <= 2.0:
            bias = "BEARISH"
        elif avg_score <= 2.5:
            bias = "LEAN_BEARISH"
        else:
            bias = "NEUTRAL"

        # Override to cautious if high regulatory risk
        if data["regulatory_count"] > 0 and bias in ("BULLISH", "LEAN_BULLISH"):
            bias = f"{bias} (REG_RISK)"

        results[asset] = {
            "score": round(avg_score, 2),
            "count": data["count"],
            "bias": bias,
            "avg_score": round(sum(data["raw_scores"]) / len(data["raw_scores"]), 2),
            "material_count": data["material_count"],
            "regulatory_count": data["regulatory_count"],
        }

    return results


def print_sentiment_report(aggregated: dict):
    """Pretty-print the sentiment report."""
    print("\n" + "=" * 60)
    print("  CRYPTO SENTIMENT REPORT")
    print("=" * 60)

    if not aggregated:
        print("  No judged articles available.")
        return

    for asset, data in sorted(aggregated.items()):
        score = data["score"]
        bias = data["bias"]
        count = data["count"]
        material = data["material_count"]
        reg = data["regulatory_count"]

        # Sentiment bar
        bar_len = int(score * 4)
        bar = "█" * bar_len + "░" * (20 - bar_len)

        print(f"\n  {asset}:")
        print(f"    Score: {score}/5.0  [{bar}]")
        print(f"    Bias:  {bias}")
        print(f"    Articles: {count} | Material: {material} | Regulatory: {reg}")

    print("\n" + "=" * 60)
