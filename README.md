# Jev News Sentiment Bot

Crypto news sentiment analysis powered by [Jev typed decisions](https://openrouter.ai/api/alpha/decisions).

## What It Does

1. **Fetches** crypto news from 5 RSS sources (CoinDesk, Cointelegraph, Bitcoin Magazine, Decrypt, The Block)
2. **Judges** each article via Jev with 4 typed decisions:
   - **Asset** (choice): BTC / ETH / SOL / XRP / other
   - **Sentiment** (score): very-negative → very-positive (1-5)
   - **Materiality** (noul): Is this price-moving?
   - **Regulatory risk** (noul): Does this involve regulation?
3. **Aggregates** sentiment per asset with exponential time decay
4. **Outputs** trading bias: BULLISH / LEAN_BULLISH / NEUTRAL / LEAN_BEARISH / BEARISH

## Setup

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv pyyaml feedparser

# Configure API key
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

## Usage

```bash
# Fetch news from RSS feeds
python run.py fetch

# Fetch + judge via Jev (requires OPENROUTER_API_KEY)
python run.py judge

# Continuous monitoring (fetch + judge every 5 min)
python run.py monitor

# View last sentiment report
python run.py stats
```

## Output

The sentiment report shows per-asset:
- **Score**: Weighted average (1-5) with time decay
- **Bias**: Trading signal based on score thresholds
- **Article count**: Number of articles judged
- **Material**: Articles flagged as price-moving
- **Regulatory**: Articles flagged with regulatory risk

## Architecture

```
RSS Feeds → news_fetcher.py → [Article objects]
                                    ↓
              jev_client.py ← Jev API (OpenRouter)
                                    ↓
              sentiment.py → aggregate with decay → trading bias
                                    ↓
              logger.py → data/sentiment_log.jsonl
```

## Files

| File | Purpose |
|------|---------|
| `news_fetcher.py` | RSS feed fetching + Article class |
| `jev_client.py` | Jev typed-decision API client |
| `sentiment.py` | Judgment orchestration + aggregation |
| `logger.py` | JSONL structured logging |
| `run.py` | CLI entry point |
| `config.yaml` | Feed URLs, Jev config, thresholds |
| `.env.example` | API key template |

## Data

- `data/fetched_articles.json` — Latest fetched articles
- `data/sentiment_report.json` — Latest aggregated report
- `data/sentiment_log.jsonl` — Full event log
