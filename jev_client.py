"""Jev typed-decision client via OpenRouter."""
import os
import requests
from typing import Optional


JEV_ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
JEV_MODEL = "typesafe/jev-1.13"


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key.")
    return key


def judge_article(title: str, summary: str) -> Optional[dict]:
    """Send an article to Jev for typed-decision judgment.

    Returns dict with keys: asset, sentiment, sentiment_score, material, regulatory
    or None on failure.
    """
    state = f"ARTICLE TITLE: {title}\n\nARTICLE SUMMARY: {summary[:1000]}"

    body = {
        "model": JEV_MODEL,
        "state": state,
        "questions": {
            "asset": {
                "type": "choice",
                "instructions": "Which cryptocurrency asset is this article primarily about?",
                "criteria": {
                    "BTC": "Bitcoin - the article is about Bitcoin/BTC",
                    "ETH": "Ethereum - the article is about Ethereum/ETH",
                    "SOL": "Solana - the article is about Solana/SOL",
                    "XRP": "XRP/Ripple - the article is about XRP or Ripple",
                    "other": "The article is about another asset or crypto in general",
                },
            },
            "sentiment": {
                "type": "score",
                "instructions": "What is the sentiment of this article toward the crypto asset?",
                "criteria": [
                    "very-negative: extremely bearish, major bad news, hack, crash, ban",
                    "negative: bearish tone, decline, lawsuit, criticism",
                    "neutral: informational, no clear bullish or bearish lean",
                    "positive: bullish, adoption, partnership, price rise",
                    "very-positive: extremely bullish, major breakthrough, ETF approval, massive rally",
                ],
            },
            "material": {
                "type": "noul",
                "instructions": "Is this article material to the asset's price? Would a trader need to act on this?",
            },
            "regulatory": {
                "type": "noul",
                "instructions": "Does this article involve regulatory risk, government action, or legal issues?",
            },
        },
    }

    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(JEV_ENDPOINT, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Parse Jev response
        decisions = data.get("decisions", data)
        result = {}

        # Extract answers from Jev's response format
        for q_key in ("asset", "sentiment", "material", "regulatory"):
            q_data = decisions.get(q_key, {})
            # Jev may return answer directly or nested
            answer = q_data.get("answer", q_data.get("value", q_data))
            result[q_key] = answer

        # Map sentiment to numeric score
        sentiment_map = {
            "very-negative": 1.0,
            "negative": 2.0,
            "neutral": 3.0,
            "positive": 4.0,
            "very-positive": 5.0,
        }
        # Jev score type may return as string label
        sent_raw = str(result.get("sentiment", "neutral")).lower().strip()
        result["sentiment_score"] = sentiment_map.get(sent_raw, 3.0)

        # Normalize noul to bool
        for key in ("material", "regulatory"):
            val = result.get(key)
            if isinstance(val, str):
                result[key] = val.lower() in ("true", "yes", "1")
            elif isinstance(val, (int, float)):
                result[key] = bool(val)

        return result

    except requests.exceptions.HTTPError as e:
        print(f"  [!] Jev API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"      Response: {e.response.text[:300]}")
        return None
    except Exception as e:
        print(f"  [!] Jev request failed: {e}")
        return None
