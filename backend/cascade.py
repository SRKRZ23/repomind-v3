"""
Confidence-gated cascade — run the CHEAP tier first, escalate to the DEEP tier only
when confidence is low.

Research basis (deep-research 2026-07, verified): FrugalGPT / UCCI / decision-theoretic
cascades deliver a REALISTIC ~15-35% cost cut at <2% accuracy loss when gated
CONSERVATIVELY — not the cherry-picked "98%". For a coding agent, correctness matters
more than a few cents, so we gate conservatively: when unsure, ESCALATE.

This module is the pure gating policy (fully unit-testable). The orchestration that
actually calls cheap→deep lives in the request handler; it uses these functions to
decide whether the deep (Fireworks) call is needed at all.
"""
import os
import re

# Escalate when cheap-tier confidence is below this. High default = conservative
# (protect code correctness; only skip the deep model when clearly confident).
ESCALATE_THRESHOLD = float(os.getenv("CASCADE_ESCALATE_THRESHOLD", "0.7"))

# Phrases that signal the cheap model is unsure → escalate.
_UNSURE = re.compile(
    r"\b(i'?m not sure|not (sure|certain)|unclear|can(?:'?t|not) (determine|tell)|"
    r"might be|possibly|i don'?t know|hard to say|would need (more|to)|"
    r"insufficient (context|information)|no (relevant|matching) (file|code))\b",
    re.I,
)


def parse_self_score(reply: str) -> float | None:
    """If the cheap model was asked to end with 'CONFIDENCE: 0.NN', extract it (0..1)."""
    m = re.search(r"CONFIDENCE:\s*([01](?:\.\d+)?)", reply or "", re.I)
    if not m:
        return None
    return max(0.0, min(1.0, float(m.group(1))))


def confidence(reply: str, self_score: float | None = None) -> float:
    """Confidence in [0,1]. Prefer an explicit self-score; else a heuristic on
    uncertainty markers + answer substance."""
    if self_score is not None:
        return max(0.0, min(1.0, self_score))
    text = (reply or "").strip()
    if not text:
        return 0.0
    c = 0.78
    if _UNSURE.search(text):
        c -= 0.45
    if len(text) < 40:  # terse answers are weak evidence for a code question
        c -= 0.15
    return round(max(0.0, min(1.0, c)), 3)


def should_escalate(conf: float, threshold: float = ESCALATE_THRESHOLD) -> bool:
    """Escalate to the deep tier when confidence < threshold (conservative: unsure → escalate)."""
    return conf < threshold


def decide(reply: str, self_score: float | None = None, threshold: float = ESCALATE_THRESHOLD) -> dict:
    """One call: turn a cheap-tier reply into a routing decision + a cost-story label."""
    conf = confidence(reply, self_score if self_score is not None else parse_self_score(reply))
    esc = should_escalate(conf, threshold)
    return {
        "confidence": conf,
        "escalate": esc,
        "tier": "deep" if esc else "cheap",
        "reason": (
            f"confidence {conf:.2f} < {threshold:.2f} → escalate to deep tier"
            if esc else
            f"confidence {conf:.2f} ≥ {threshold:.2f} → cheap tier answer accepted (deep call skipped, $ saved)"
        ),
    }
