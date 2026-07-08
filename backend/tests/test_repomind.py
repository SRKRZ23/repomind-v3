"""REPOMIND v3 unit tests — deterministic tools, router, parser, path safety."""
from pathlib import Path

import pytest

import tools
import router
import agent_loop

try:
    import fastapi  # noqa: F401
    import sse_starlette  # noqa: F401
    _API_DEPS = True
except Exception:
    _API_DEPS = False

requires_api = pytest.mark.skipif(not _API_DEPS, reason="fastapi/sse_starlette not installed")


# ── CUDA → ROCm migration ────────────────────────────────────────────────────
DEMO = Path(__file__).resolve().parent.parent.parent / "demo" / "cuda_sample.cu"


def test_migration_converts_event_destroy():
    src = "cudaEventDestroy(start); cudaEventDestroy(stop);"
    out = tools.migrate_cuda_to_rocm(src)
    assert "hipEventDestroy" in out
    # The added ('+') lines must contain no residual cudaEventDestroy.
    added = [l for l in out.splitlines() if l.startswith("+") and not l.startswith("+++")]
    assert not any("cudaEventDestroy" in l for l in added)


def test_migration_converts_kernel_launch():
    src = "matmul_kernel<<<grid, block, 0, stream>>>(d_A, d_B, d_C, N);"
    out = tools.migrate_cuda_to_rocm(src)
    assert "hipLaunchKernelGGL(matmul_kernel, grid, block, 0, stream, d_A, d_B, d_C, N)" in out


def test_full_demo_leaves_no_cuda_calls():
    """The flagship demo must fully migrate — no residual cuda* API in the '+' lines."""
    if not DEMO.exists():
        return
    out = tools.migrate_cuda_to_rocm(DEMO.read_text())
    added = [l for l in out.splitlines() if l.startswith("+") and not l.startswith("+++")]
    residual = [l for l in added if "cuda" in l.lower() and "hip" not in l.lower()]
    assert not residual, f"residual CUDA in migrated output: {residual}"
    assert "<<<" not in "".join(added), "kernel-launch syntax not converted"


def test_migration_diff_is_unified():
    out = tools.migrate_cuda_to_rocm("cudaMalloc(&d, n);")
    assert out.startswith("--- a/original.cu")
    assert "+++ b/original.cu" in out  # same basename → git apply-clean
    assert "@@" in out  # real hunk header from difflib


def test_split_patch_drops_summary():
    out = tools.migrate_cuda_to_rocm("cudaMalloc(&d, n);")
    patch = tools.split_patch(out)
    assert tools.SUMMARY_MARKER not in patch
    assert patch.startswith("--- a/original.cu")


def test_migration_patch_git_applies(tmp_path):
    """The flagship claim: the emitted diff is git apply-clean."""
    import shutil, subprocess
    if not shutil.which("git"):
        return
    src = "#include <cuda_runtime.h>\nvoid f(){ float*d; cudaMalloc(&d,16); cudaFree(d); }\n"
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "original.cu").write_text(src)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "original.cu"], cwd=repo, check=True)
    patch = tools.split_patch(tools.migrate_cuda_to_rocm(src))
    (repo / "m.patch").write_text(patch)
    r = subprocess.run(["git", "apply", "--check", "m.patch"], cwd=repo,
                       capture_output=True, text=True)
    assert r.returncode == 0, f"git apply --check failed: {r.stderr}"


def test_list_files_rejects_traversal(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    out = tools.list_files(tmp_path, "../../..")
    assert "outside the repository sandbox" in out


def test_air_gap_refuses_egress(monkeypatch):
    import asyncio
    import fireworks_client
    monkeypatch.setattr(fireworks_client, "AIR_GAP", True)
    try:
        asyncio.run(fireworks_client.gemma_complete([{"role": "user", "content": "hi"}]))
        assert False, "expected RuntimeError under AIR_GAP"
    except RuntimeError as e:
        assert "AIR_GAP" in str(e)


# ── Compliance heuristic (no false positives on the word "token") ─────────────
def test_compliance_no_false_positive_on_token_word():
    content = "### FILE: config.py\nmax_tokens = 4096\ntotal_tokens = count\n"
    report = tools.compliance_scan(content)
    assert "config.py:1" not in report  # max_tokens must NOT be flagged as a secret


def test_compliance_flags_real_secret():
    content = '### FILE: secrets.py\napi_key = "sk-prod-ABCDEF0123456789ZZ"\n'
    report = tools.compliance_scan(content)
    assert "LLM06" in report and "secrets.py:1" in report


def test_compliance_logging_indicator_precise():
    yes = tools.compliance_scan("### FILE: a.py\nimport logging\nlogging.info('x')\n")
    no = tools.compliance_scan("### FILE: b.py\nx = catalog_dialog_blog\n")
    assert "detected logging/audit API usage" in yes
    assert "no logging/audit API detected" in no


def test_compliance_labeled_as_heuristic():
    assert "HEURISTIC PRE-SCAN" in tools.compliance_scan("### FILE: a.py\nx=1\n")


# ── Path traversal is rejected ────────────────────────────────────────────────
def test_read_file_rejects_traversal(tmp_path):
    (tmp_path / "ok.txt").write_text("safe")
    assert tools.read_file(tmp_path, "ok.txt") == "safe"
    out = tools.read_file(tmp_path, "../../../../etc/passwd")
    assert "outside the repository sandbox" in out


def test_grep_rejects_traversal(tmp_path):
    out = tools.grep_codebase(tmp_path, "root", "../../..")
    assert "outside the repository sandbox" in out


# ── Router ────────────────────────────────────────────────────────────────────
def test_router_threshold():
    short = router.route("hi")
    assert short["backend"] == "fireworks"
    big = router.route("x " * 20000)
    assert big["backend"] == "mi300x"


def test_router_air_gap_forces_mi300x(monkeypatch):
    monkeypatch.setattr(router, "AIR_GAP", True)
    r = router.route("hi")
    assert r["backend"] == "mi300x"
    assert "AIR-GAP" in r["reason"]


# ── SC-TIR directive parser (markdown-tolerant, multi-line) ───────────────────
def test_directive_tolerates_markdown():
    assert agent_loop._directive("**PLAN:** do a thing")[0] == "PLAN"
    assert agent_loop._directive("1. CALL: list_files()")[0] == "CALL"
    assert agent_loop._directive("> THINK: hmm")[0] == "THINK"
    assert agent_loop._directive("random line") is None


def test_parse_tool_call():
    assert agent_loop._parse_tool_call("read_file(README.md)") == ("read_file", "README.md")
    assert agent_loop._parse_tool_call("not a call") is None


def test_agent_detects_bad_observation():
    # Failures/empty → trigger self-recovery re-plan
    assert agent_loop._is_bad_observation("ERROR: foo not found")
    assert agent_loop._is_bad_observation("outside the repository sandbox (rejected)")
    assert agent_loop._is_bad_observation("No matches for 'x'")
    assert agent_loop._is_bad_observation("   ")
    # Real content → keep going
    assert not agent_loop._is_bad_observation("def main():\n    return 1")


# ── Gemma triage ──────────────────────────────────────────────────────────────
import triage


def test_triage_parse_selection():
    valid = {"a.py", "b.py"}
    assert triage.parse_selection('["a.py","x.py"]', valid) == ["a.py"]
    assert triage.parse_selection("no json here", valid) == []
    assert triage.parse_selection('sure: ["b.py", "b.py"]', valid) == ["b.py"]
    assert triage.parse_selection('["./a.py"]', valid) == ["a.py"]


def test_triage_reduces_context(monkeypatch, tmp_path):
    import asyncio
    from git_fetcher import file_manifest
    (tmp_path / "a.py").write_text("relevant\n" * 40)
    (tmp_path / "big.py").write_text("noise\n" * 4000)

    async def fake_gemma(msgs, max_tokens=512):
        return {"content": '["a.py"]', "cost_usd": 0.0001, "model": "gemma3-27b-it"}
    monkeypatch.setattr(triage, "gemma_complete", fake_gemma)

    manifest = file_manifest(tmp_path)
    res = asyncio.run(triage.gemma_triage(tmp_path, "explain a", manifest, lambda s: len(s) // 4))
    assert res is not None
    assert res["selected"] == ["a.py"]
    assert 0 < res["focused_tokens"] < res["full_tokens"]
    assert res["reduction_pct"] > 50  # dropped the big noise file


def test_audit_chain_tamper_evident(tmp_path, monkeypatch):
    import audit
    p = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_PATH", p)
    monkeypatch.setattr(audit, "_SEQ", 0)
    monkeypatch.setattr(audit, "_LAST_HASH", "0" * 64)
    sid = audit.new_session(["u"], "q", "analyze")
    audit.record(sid, "plan", {"x": 1})
    audit.record(sid, "answer", {"y": 2})
    ok, n = audit.verify_chain(p)
    assert ok and n == 3
    # tamper with a middle record → chain must break
    lines = p.read_text().splitlines()
    import json as J
    rec = J.loads(lines[1]); rec["payload"] = {"x": 999}; lines[1] = J.dumps(rec)
    p.write_text("\n".join(lines) + "\n")
    ok2, _ = audit.verify_chain(p)
    assert not ok2


def test_audit_ed25519_signatures(tmp_path, monkeypatch):
    import audit
    if not audit._CRYPTO:
        return  # cryptography not installed locally; runs in Docker
    p = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_PATH", p)
    monkeypatch.setattr(audit, "_SEQ", 0)
    monkeypatch.setattr(audit, "_LAST_HASH", "0" * 64)
    sid = audit.new_session(["u"], "q", "analyze")
    audit.record(sid, "answer", {"y": 1})
    ok, n = audit.verify_signatures(p)
    assert ok and n >= 2  # every record signed and verifiable
    # corrupt a signature → verification must fail
    import json as J
    lines = p.read_text().splitlines()
    rec = J.loads(lines[0]); rec["sig"] = "00" * 64; lines[0] = J.dumps(rec)
    p.write_text("\n".join(lines) + "\n")
    ok2, _ = audit.verify_signatures(p)
    assert not ok2


def test_audit_key_pinning_rejects_foreign_key(tmp_path, monkeypatch):
    import audit
    if not audit._CRYPTO:
        return
    p = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_PATH", p)
    monkeypatch.setattr(audit, "_SEQ", 0)
    monkeypatch.setattr(audit, "_LAST_HASH", "0" * 64)
    sid = audit.new_session(["u"], "q", "analyze")
    # verifies against the real key, but a DIFFERENT pinned key must be rejected (anti-forgery)
    ok_real, _ = audit.verify_signatures(p, expected_pubkey=audit._PUB_HEX)
    ok_wrong, _ = audit.verify_signatures(p, expected_pubkey="ab" * 32)
    assert ok_real and not ok_wrong


def test_triage_falls_back_on_gemma_error(monkeypatch, tmp_path):
    import asyncio
    from git_fetcher import file_manifest
    (tmp_path / "a.py").write_text("x\n")

    async def boom(msgs, max_tokens=512):
        raise RuntimeError("AIR_GAP=1")
    monkeypatch.setattr(triage, "gemma_complete", boom)
    res = asyncio.run(triage.gemma_triage(tmp_path, "q", file_manifest(tmp_path), lambda s: len(s) // 4))
    assert res is None  # caller falls back to full context


# ── API: auth + validation + /analyze integration ────────────────────────────
def _client():
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app), main


@requires_api
def test_analyze_rejects_bad_url(monkeypatch):
    client, main = _client()
    monkeypatch.setattr(main, "API_KEY", "")
    r = client.post("/analyze", json={"repo_urls": ["not-a-url"], "question": "hi"})
    assert r.status_code == 400


@requires_api
def test_auth_required_when_key_set(monkeypatch):
    client, main = _client()
    monkeypatch.setattr(main, "API_KEY", "secret")
    r = client.post("/analyze", json={"repo_urls": ["https://github.com/o/r"], "question": "hi"})
    assert r.status_code == 401


@requires_api
def test_analyze_streams_with_auth(monkeypatch, tmp_path):
    client, main = _client()
    monkeypatch.setattr(main, "API_KEY", "secret")
    monkeypatch.setattr(main, "clone_or_pull", lambda url: tmp_path)
    monkeypatch.setattr(main, "pack_repo", lambda p: "### FILE: a.py\nprint(1)\n")  # small → fireworks, no triage

    async def fake_agent(q, path, ctx, backend, routing):
        yield 'data: {"step":"plan","content":"planning"}\n\n'
        yield 'data: {"step":"answer","content":"DONE","meta":{"total_cost":"$0","tool_calls":0}}\n\n'
    monkeypatch.setattr(main, "run_agent", fake_agent)

    r = client.post("/analyze",
                    headers={"X-API-Key": "secret"},
                    json={"repo_urls": ["https://github.com/o/r"], "question": "hi"})
    assert r.status_code == 200
    assert "DONE" in r.text and "answer" in r.text
