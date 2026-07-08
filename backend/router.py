import os

ROUTING_THRESHOLD = int(os.getenv("ROUTING_THRESHOLD", "8000"))
# Enforced on-prem posture: when set, ALL queries go to the MI300X and the
# external Fireworks/Gemma path is refused at the client (see fireworks_client).
AIR_GAP = os.getenv("AIR_GAP", "0") not in ("0", "", "false", "False")

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
except Exception:
    _enc = None


def count_tokens(text: str) -> int:
    # cl100k_base is an approximation for Qwen/Gemma tokenization — used only to
    # pick a routing tier, not for billing, so a ~10-15% drift is acceptable.
    if _enc:
        return len(_enc.encode(text))
    return len(text) // 4  # fallback: ~4 chars per token


def route(context: str) -> dict:
    """
    Decide which backend to use.
    AIR_GAP set → always MI300X (zero external egress).
    < ROUTING_THRESHOLD tokens → Gemma via Fireworks (fast, cheap).
    ≥ ROUTING_THRESHOLD tokens → AMD MI300X vLLM (deep, 256K).
    """
    tokens = count_tokens(context)
    if AIR_GAP or tokens >= ROUTING_THRESHOLD:
        reason = (
            f"{tokens:,} tokens → AMD MI300X · Qwen3-Coder-Next-FP8 · 256K context"
            + (" [AIR-GAP: on-prem only]" if AIR_GAP else "")
        )
        return {
            "backend": "mi300x",
            "tokens": tokens,
            "reason": reason,
            "est_cost_usd": (tokens / 1000) * 0.00028,
            "est_latency_s": "15–90s",
        }
    return {
        "backend": "fireworks",
        "tokens": tokens,
        "reason": f"{tokens:,} tokens → Gemma 27B via Fireworks AI (first-pass fast tier)",
        "est_cost_usd": (tokens / 1000) * 0.0009,
        "est_latency_s": "1–3s",
    }
