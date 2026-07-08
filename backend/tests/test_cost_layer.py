"""REPOMIND cost-layer tests: cost_meter, cascade gating, code skeleton."""
import cost_meter
import cascade
import code_skeleton


# ── cost_meter ──────────────────────────────────────────────────────────────
def test_cache_makes_a_call_cheaper():
    cold = cost_meter.call_cost(6000, 100, 0, 0.0009, 0.0009)
    warm = cost_meter.call_cost(6000, 100, 5900, 0.0009, 0.0009)
    assert warm["actual_usd"] < cold["actual_usd"]
    assert warm["cache_saved_usd"] > 0
    assert warm["cache_hit_pct"] == 98


def test_no_cache_no_saving():
    c = cost_meter.call_cost(1000, 50, 0, 0.0009, 0.0009)
    assert c["cache_saved_usd"] == 0 and c["cache_hit_pct"] == 0


def test_triage_saved_tokens_and_pct():
    t = cost_meter.triage_saved(50000, 12000, 0.0009)
    assert t["saved_tokens"] == 38000 and t["reduction_pct"] == 76


def test_savings_report_headline():
    r = cost_meter.savings_report(
        50000, 12000, {"prompt_tokens": 6000, "completion_tokens": 100, "cached_tokens": 5900},
        0.0009, 0.0009,
    )
    assert r["total_saved_usd"] > 0 and "saved this query" in r["headline"]


# ── cascade gating ──────────────────────────────────────────────────────────
def test_confident_reply_stays_cheap():
    d = cascade.decide("module_5 returns (x*5) % 97. CONFIDENCE: 0.95")
    assert d["escalate"] is False and d["tier"] == "cheap"


def test_unsure_reply_escalates():
    d = cascade.decide("I'm not sure, this might be in another file — hard to say.")
    assert d["escalate"] is True and d["tier"] == "deep"


def test_self_score_is_honoured():
    assert cascade.parse_self_score("answer... CONFIDENCE: 0.3") == 0.3
    assert cascade.should_escalate(0.3) is True
    assert cascade.should_escalate(0.9) is False


# ── code skeleton ───────────────────────────────────────────────────────────
def test_skeleton_keeps_signatures_drops_bodies():
    src = (
        "import os\n"
        "def add(a, b):\n"
        "    total = a + b  # body\n"
        "    return total\n"
        "class Foo:\n"
        "    def bar(self):\n"
        "        secret = compute()\n"
        "        return secret\n"
    )
    sk = code_skeleton.skeletonize(src)
    assert "import os" in sk
    assert "def add(a, b):" in sk and "class Foo:" in sk and "def bar(self):" in sk
    assert "total = a + b" not in sk and "secret = compute()" not in sk
    assert "..." in sk


def test_skeleton_reduces_tokens():
    src = "\n".join(
        f"def f{i}(x):\n    y = x * {i}\n    z = y + {i}\n    return z % 97" for i in range(50)
    )
    sk = code_skeleton.skeletonize(src)
    assert len(sk) < len(src) * 0.6


def test_compress_repo_context_preserves_headers():
    packed = "# FILE: a.py\ndef a():\n    x = 1\n    return x\n# FILE: b.py\ndef b():\n    return 2\n"
    out = code_skeleton.compress_repo_context(packed)
    assert "# FILE: a.py" in out and "# FILE: b.py" in out
    assert "def a():" in out and "def b():" in out
    assert "x = 1" not in out
