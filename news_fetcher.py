"""Fetch crypto news from multiple RSS feeds."""
import feedparser
from datetime import datetime, timezone
from typing import Optional


# Keyword map to help pre-classify articles by asset
ASSET_KEYWORDS = {
    "BTC": ["bitcoin", "btc", "satoshi"],
    "ETH": ["ethereum", "eth", "vitalik", "ether"],
    "SOL": ["solana", "sol"],
    "XRP": ["xrp", "ripple"],
}


class Article:
    def __init__(self, title: str, summary: str, url: str, source: str,
                 published: Optional[datetime] = None):
        self.title = title
        self.summary = summary
        self.url = url
        self.source = source
        self.published = published or datetime.now(timezone.utc)
        self.asset: Optional[str] = None
        self.sentiment: Optional[str] = None
        self.material: Optional[bool] = None
        self.regulatory: Optional[bool] = None
        self.sentiment_score: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary[:500],
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat(),
            "asset": self.asset,
            "sentiment": self.sentiment,
            "material": self.material,
            "regulatory": self.regulatory,
            "sentiment_score": self.sentiment_score,
        }

    def __repr__(self):
        return f"Article({self.source}: {self.title[:60]}...)"


def guess_asset(text: str) -> Optional[str]:
    """Quick keyword-based asset guess for pre-filtering."""
    lower = text.lower()
    for asset, keywords in ASSET_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return asset
    return None


def parse_pub_date(entry) -> Optional[datetime]:
    """Try to parse published date from feed entry."""
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except Exception:
                pass
    return None


def fetch_feed(name: str, url: str) -> list[Article]:
    """Fetch and parse a single RSS feed."""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            link = getattr(entry, "link", "")
            published = parse_pub_date(entry)

            article = Article(
                title=title,
                summary=summary,
                url=link,
                source=name,
                published=published,
            )
            articles.append(article)
    except Exception as e:
        print(f"  [!] Error fetching {name}: {e}")
    return articles


def fetch_all(feeds_config: list[dict]) -> list[Article]:
    """Fetch articles from all configured feeds."""
    all_articles = []
    for feed_cfg in feeds_config:
        name = feed_cfg["name"]
        url = feed_cfg["url"]
        print(f"  Fetching {name}...")
        articles = fetch_feed(name, url)
        print(f"    -> {len(articles)} articles")
        all_articles.extend(articles)
    return all_articles
