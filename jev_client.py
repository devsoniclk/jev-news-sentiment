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

        # Jev returns answers keyed by question name
        answers = data.get("answers", {})
        result = {}

        # Extract asset from choice type
        asset_q = answers.get("asset", {})
        result["asset"] = asset_q.get("choice", "other")

        # Extract sentiment from score type — normalize to 1-5
        sent_q = answers.get("sentiment", {})
        raw_score = sent_q.get("score", 1.0)
        num_criteria = len(body["questions"]["sentiment"]["criteria"])
        max_idx = num_criteria - 1
        if max_idx > 0:
            result["sentiment_score"] = round(1.0 + (raw_score / max_idx) * 4.0, 2)
        else:
            result["sentiment_score"] = 3.0

        # Derive sentiment label from score
        ss = result["sentiment_score"]
        if ss <= 1.5:
            result["sentiment"] = "very-negative"
        elif ss <= 2.5:
            result["sentiment"] = "negative"
        elif ss <= 3.5:
            result["sentiment"] = "neutral"
        elif ss <= 4.5:
            result["sentiment"] = "positive"
        else:
            result["sentiment"] = "very-positive"

        # Extract noul type values (probability 0-1) → bool at 0.5 threshold
        for key in ("material", "regulatory"):
            noul_q = answers.get(key, {})
            prob = noul_q.get("noul", 0.0)
            result[key] = prob >= 0.5

        return result

    except requests.exceptions.HTTPError as e:
        print(f"  [!] Jev API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"      Response: {e.response.text[:300]}")
        return None
    except Exception as e:
        print(f"  [!] Jev request failed: {e}")
        return None
