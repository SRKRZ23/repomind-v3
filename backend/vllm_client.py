import os
import httpx

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8080")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "token-repomind")
# Verified on AMD MI300X in ACT I: Qwen3-Coder-Next-FP8 (80B total / 3B active MoE)
# served at --max-model-len 262144 (256K). Weights 77.29 GiB, KV cache 94.58 GiB
# available, 176 GiB / 192 GiB peak. See Zenodo 10.5281/zenodo.20330468.
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen3-Coder-Next-FP8")
MODEL_DISPLAY = "Qwen3-Coder-Next-FP8 (AMD MI300X 192GB)"

# MI300X cost basis: ~$1.99/hr rental. ~2000 tok/s → ~$0.00028 per 1K tokens.
COST_PER_1K_TOKENS = 0.00028


async def mi300x_complete(messages: list[dict], max_tokens: int = 4096) -> dict:
    """Call Qwen3-Coder-Next-FP8 on AMD MI300X via vLLM. Returns {content, tokens, cost_usd}"""
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{VLLM_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {VLLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": VLLM_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    total_tok = usage.get("total_tokens", 0)
    cost = (total_tok / 1000) * COST_PER_1K_TOKENS

    return {"content": content, "total_tokens": total_tok, "cost_usd": cost, "model": MODEL_DISPLAY}
