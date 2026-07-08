"""
Gemma first-pass triage.

For large repositories, the expensive MI300X deep pass does not need the *entire*
codebase in context. Gemma 27B (via Fireworks) reads a compact file manifest + the user's
question and selects the handful of files actually relevant to the answer. That focused
subset is what the MI300X then reasons over deeply.

This makes Gemma load-bearing (not a disposable cheap tier): it does real work the big
model would otherwise waste 256K-context compute on, and we quantify the token reduction.

Disabled under AIR_GAP (no external egress) — there the MI300X handles the full context.
"""
import asyncio
import json
import re

from fireworks_client import gemma_complete
from git_fetcher import pack_selected

MAX_SELECTED = 15


def _build_prompt(manifest, question: str, broaden: bool = False) -> str:
    index = "\n".join(f"- {rel}  (~{tok} tok) — {first}" for rel, tok, first in manifest)
    extra = (
        "\nThe first pass may have MISSED relevant files — include related modules, "
        "tests, and config, and select a BROADER set this time.\n" if broaden else ""
    )
    return (
        "You are a code-triage assistant. Given a repository file index and a question, "
        f"select up to {MAX_SELECTED} files MOST relevant to answering it.\n\n"
        f"FILE INDEX:\n{index}\n\n"
        f"QUESTION: {question}\n{extra}\n"
        'Reply with ONLY a JSON array of file paths, e.g. ["src/a.py","README.md"]. '
        "No prose."
    )


def _sufficient(selected: list, manifest, question: str) -> bool:
    """Agentic self-check: does the selection look like it can answer the question?"""
    if not selected:
        return False
    if len(manifest) <= 3:
        return True  # tiny repo — any valid pick covers it
    kws = set(re.findall(r"[a-z0-9_]{3,}", question.lower()))
    if any(any(k in p.lower() for k in kws) for p in selected):
        return True  # a selected path matches a question keyword → on-target
    return len(selected) >= 2  # otherwise trust a multi-file pick


def parse_selection(text: str, valid_paths: set) -> list:
    """Extract a JSON array of paths from Gemma's reply; keep only valid, de-duped paths."""
    m = re.search(r"\[.*?\]", text, re.DOTALL)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except Exception:
        return []
    seen, out = set(), []
    for p in raw:
        if isinstance(p, str):
            p = p.strip().strip("./")
            if p in valid_paths and p not in seen:
                seen.add(p)
                out.append(p)
    return out[:MAX_SELECTED]


async def gemma_triage(repo_path, question: str, manifest, count_tokens, max_rounds: int = 2) -> dict | None:
    """
    Agentic-RAG triage: select relevant files, self-check sufficiency, and re-select
    (broader) ONCE if the first pass looks thin — bounded to max_rounds to cap cost.
    Returns a focused-context dict, or None to fall back to full context.
    """
    if not manifest:
        return None
    valid = {rel for rel, _, _ in manifest}
    full_tokens = sum(tok for _, tok, _ in manifest)

    selected, rounds, cost, model, broaden = [], 0, 0.0, "gemma3-27b-it (Fireworks)", False
    while rounds < max_rounds:
        rounds += 1
        try:
            result = await gemma_complete(
                [{"role": "user", "content": _build_prompt(manifest, question, broaden)}],
                max_tokens=512,
            )
        except Exception:
            break  # air-gap refusal / missing key / network error → fall back below
        cost += result.get("cost_usd", 0.0)
        model = result.get("model", model)
        sel = parse_selection(result.get("content", ""), valid)
        if sel:
            selected = sel
        if _sufficient(selected, manifest, question):
            break
        broaden = True  # next round asks for a broader set

    if not selected:
        return None

    focused = await asyncio.to_thread(pack_selected, repo_path, selected)
    # Use the SAME approximation as the manifest (len//4) on both sides so the
    # reduction ratio is apples-to-apples, not skewed by two different tokenizers.
    focused_tokens = max(1, len(focused) // 4)
    reduction = 0 if full_tokens <= 0 else max(0, round(100 * (1 - focused_tokens / full_tokens)))

    return {
        "selected": selected,
        "focused_context": focused,
        "full_tokens": full_tokens,
        "focused_tokens": focused_tokens,
        "reduction_pct": reduction,
        "cost_usd": cost,
        "model": model,
        "rounds": rounds,
        "sufficient": _sufficient(selected, manifest, question),
    }
