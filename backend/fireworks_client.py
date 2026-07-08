import os
import httpx

import cost_meter

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "")
# Stable session id → Fireworks `x-session-affinity` routes repeat calls to the same worker,
# maximizing prompt-cache hit rate on the repeated repo/system prefix (lossless cost cut).
FIREWORKS_SESSION = os.getenv("FIREWORKS_SESSION", "repomind")
FIREWORKS_BASE = os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
# Gemma is NOT on Fireworks serverless for the ACT II event, so the Fireworks-tier model is
# env-configurable (e.g. accounts/fireworks/models/deepseek-v4-pro). Constant names kept for
# backwards-compat with existing imports/tests. In the ACT II demo, Gemma runs LOCALLY on the
# 48GB AMD Radeon and this Fireworks tier serves the deep-reasoning ("burst") pass.
GEMMA_MODEL = os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/gemma3-27b-it")
GEMMA_DISPLAY = os.getenv("FIREWORKS_DISPLAY", GEMMA_MODEL.rsplit("/", 1)[-1] + " (Fireworks)")

# When AIR_GAP=1 the enterprise runs fully on-prem: any attempt to reach the
# external Fireworks endpoint is hard-refused, not merely routed around. This is
# an enforced trust boundary, not an advisory env var.
AIR_GAP = os.getenv("AIR_GAP", "0") not in ("0", "", "false", "False")

# Cost estimate ($/1K tokens). Override per model via env — set these to the actual
# price of FIREWORKS_MODEL so the live "$ saved" economics number is accurate.
COST_PER_1K_INPUT = float(os.getenv("FIREWORKS_COST_PER_1K_INPUT", "0.0009"))
COST_PER_1K_OUTPUT = float(os.getenv("FIREWORKS_COST_PER_1K_OUTPUT", "0.0009"))


async def gemma_complete(messages: list[dict], max_tokens: int = 2048) -> dict:
    """Call Gemma 27B via Fireworks AI. Returns {content, input_tokens, output_tokens, cost_usd}"""
    if AIR_GAP:
        raise RuntimeError(
            "AIR_GAP=1: external Fireworks/Gemma egress is disabled. "
            "Route all queries on-prem via MI300X (set ROUTING_THRESHOLD=0)."
        )
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{FIREWORKS_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
                "x-session-affinity": FIREWORKS_SESSION,
            },
            json={
                "model": GEMMA_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    in_tok = usage.get("prompt_tokens", 0)
    out_tok = usage.get("completion_tokens", 0)
    cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    c = cost_meter.call_cost(in_tok, out_tok, cached, COST_PER_1K_INPUT, COST_PER_1K_OUTPUT)

    return {
        "content": content,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cached_tokens": cached,
        "cost_usd": c["actual_usd"],
        "cache_saved_usd": c["cache_saved_usd"],
        "model": GEMMA_DISPLAY,
    }
