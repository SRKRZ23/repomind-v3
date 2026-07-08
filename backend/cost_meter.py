"""
Cost & Savings meter — turns REAL token usage into a live "$ saved" number.

REPOMIND cuts inference cost with two measured levers (both computed from actual
provider usage, never projected):
  1. Prompt caching (Fireworks, on by default): the repeated repo/system prefix bills
     at a discount — we read `cached_tokens` from usage and price those cheaper.
  2. Gemma triage: focuses the context so the deep model processes fewer tokens.

Every figure here comes from numbers the provider actually returned, so the demo can
show "economics that pencil out" honestly, on screen.
"""
import os

# Cached prompt tokens bill at this fraction of the normal input price (Fireworks ~50%).
CACHE_DISCOUNT = float(os.getenv("FIREWORKS_CACHE_DISCOUNT", "0.5"))


def call_cost(
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int,
    price_in_per_1k: float,
    price_out_per_1k: float,
    cache_discount: float = CACHE_DISCOUNT,
) -> dict:
    """Actual $ for one call, the $ it WOULD have cost with no cache, and the saving."""
    cached = max(0, min(cached_tokens, prompt_tokens))
    uncached_prompt = prompt_tokens - cached
    actual = (
        (uncached_prompt / 1000) * price_in_per_1k
        + (cached / 1000) * price_in_per_1k * cache_discount
        + (completion_tokens / 1000) * price_out_per_1k
    )
    no_cache = (prompt_tokens / 1000) * price_in_per_1k + (completion_tokens / 1000) * price_out_per_1k
    saved = max(0.0, no_cache - actual)
    return {
        "actual_usd": round(actual, 6),
        "no_cache_usd": round(no_cache, 6),
        "cache_saved_usd": round(saved, 6),
        "cached_tokens": cached,
        "cache_hit_pct": (round(100 * cached / prompt_tokens) if prompt_tokens else 0),
    }


def triage_saved(full_tokens: int, focused_tokens: int, price_in_per_1k: float) -> dict:
    """$ the deep model did NOT spend because triage focused the context."""
    saved_tokens = max(0, full_tokens - focused_tokens)
    return {
        "saved_tokens": saved_tokens,
        "triage_saved_usd": round((saved_tokens / 1000) * price_in_per_1k, 6),
        "reduction_pct": (round(100 * saved_tokens / full_tokens) if full_tokens else 0),
    }


def savings_report(
    full_tokens: int,
    focused_tokens: int,
    deep_usage: dict,
    price_in_per_1k: float,
    price_out_per_1k: float,
) -> dict:
    """
    One combined economics line for the demo/video.
    `deep_usage` = {prompt_tokens, completion_tokens, cached_tokens} from the deep call.
    """
    triage = triage_saved(full_tokens, focused_tokens, price_in_per_1k)
    call = call_cost(
        deep_usage.get("prompt_tokens", 0),
        deep_usage.get("completion_tokens", 0),
        deep_usage.get("cached_tokens", 0),
        price_in_per_1k,
        price_out_per_1k,
    )
    total_saved = round(triage["triage_saved_usd"] + call["cache_saved_usd"], 6)
    return {
        "triage": triage,
        "cache": call,
        "total_saved_usd": total_saved,
        "headline": (
            f"triage −{triage['reduction_pct']}% context "
            f"({triage['saved_tokens']:,} tok) + cache {call['cache_hit_pct']}% hit "
            f"→ ${total_saved:.4f} saved this query"
        ),
    }
