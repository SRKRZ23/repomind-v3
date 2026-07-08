import asyncio
import hmac
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()  # load .env for non-Docker (make dev-backend) runs

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from git_fetcher import clone_or_pull, pack_repo, get_repo_name, file_manifest
from router import route, count_tokens, AIR_GAP
from agent_loop import run_agent
from triage import gemma_triage
import audit
import cost_meter

app = FastAPI(title="REPOMIND v3", version="3.0.0")

# Optional API-key auth on the control plane. If API_KEY is set, /analyze and
# /cuda-to-rocm require a matching `Authorization: Bearer <key>` or `X-API-Key` header.
# Unset → open (local demo); a warning surfaces in /health.
API_KEY = os.getenv("API_KEY", "")
GEMMA_TRIAGE = os.getenv("GEMMA_TRIAGE", "1") not in ("0", "", "false", "False")
# Deep-tier $/1K input — prices the tokens triage saved (live "economics" event).
DEEP_COST_PER_1K = float(os.getenv("DEEP_COST_PER_1K_INPUT", os.getenv("FIREWORKS_COST_PER_1K_INPUT", "0.0009")))


def require_auth(authorization: str = Header(None), x_api_key: str = Header(None)):
    if not API_KEY:
        return  # open demo mode
    token = authorization[7:] if (authorization or "").startswith("Bearer ") else (x_api_key or "")
    if not hmac.compare_digest(token, API_KEY):  # constant-time compare
        raise HTTPException(401, "Missing or invalid API key")

# CORS: default permissive for local demo; lock down via ALLOWED_ORIGINS in prod.
_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

GITHUB_RE = re.compile(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+/?")


class AnalyzeRequest(BaseModel):
    repo_urls: list[str]
    question: str
    mode: str = "analyze"  # "analyze" | "cuda_rocm" | "compliance"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "3.0.0",
        "egress": "on-prem only (AIR_GAP)" if AIR_GAP else "smart routing (Gemma via Fireworks enabled)",
        "auth": "api-key required" if API_KEY else "OPEN (set API_KEY to require auth)",
        "gemma_triage": GEMMA_TRIAGE and not AIR_GAP,
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest, _=Depends(require_auth)):
    for url in req.repo_urls:
        if not GITHUB_RE.fullmatch(url.strip()):
            raise HTTPException(400, f"Invalid GitHub URL: {url}")

    sid = audit.new_session(req.repo_urls, req.question, req.mode)

    async def event_stream():
        def _sse(step: str, content: str, meta: dict = None) -> dict:
            payload = {"step": step, "content": content}
            if meta:
                payload["meta"] = meta
            audit.record(sid, step, payload)  # persist every step (EU AI Act Art. 12)
            return {"data": json.dumps(payload)}

        try:
            packed_parts = []
            primary_path = None
            for url in req.repo_urls:
                repo_name = get_repo_name(url)
                yield _sse("fetch", f"Cloning {repo_name}...")
                repo_path = await asyncio.to_thread(clone_or_pull, url)
                if primary_path is None:
                    primary_path = repo_path  # reuse for tool calls — no second clone
                packed = await asyncio.to_thread(pack_repo, repo_path)
                packed_parts.append(f"# REPO: {repo_name}\n{packed}")
                yield _sse("fetch", f"Loaded {repo_name}: {count_tokens(packed):,} tokens")

            full_context = "\n\n".join(packed_parts)

            question = req.question
            if req.mode == "cuda_rocm":
                question = ("Analyze all CUDA code in this repository and generate a HIP/ROCm "
                            "migration. Use migrate_cuda_to_rocm on the CUDA files you find.")
            elif req.mode == "compliance":
                question = ("Run the security/compliance heuristic pre-scan. Use compliance_scan, "
                            "then grep for risky exec surfaces and hardcoded secrets. Summarize the "
                            "5 OWASP-LLM risk surfaces and the EU AI Act Art. 12 record-keeping indicator. "
                            "Be explicit that this is a heuristic pre-scan, not a certified control.")

            routing = route(full_context)
            backend = routing["backend"]

            # ── Gemma first-pass triage (smart-routing mode, deep queries) ──
            # Gemma selects the relevant files so the MI300X deep pass isn't fed the
            # whole codebase — real, quantified work, not a disposable cheap tier.
            agent_context = full_context
            # Triage only for single-repo deep queries — for multi-repo we keep the full
            # concatenated context so no secondary repo is silently dropped.
            if backend == "mi300x" and GEMMA_TRIAGE and not AIR_GAP and len(req.repo_urls) == 1:
                yield _sse("triage", "Gemma 27B triaging relevant files...")
                manifest = await asyncio.to_thread(file_manifest, primary_path)
                tri = await gemma_triage(primary_path, question, manifest, count_tokens)
                if tri and tri["focused_tokens"] > 0:
                    agent_context = tri["focused_context"]
                    yield _sse(
                        "triage",
                        (f"Gemma selected {len(tri['selected'])} files → "
                         f"{tri['reduction_pct']}% context reduction "
                         f"({tri['full_tokens']:,} → {tri['focused_tokens']:,} tok)"),
                        {"selected": tri["selected"],
                         "gemma_cost": f"${tri['cost_usd']:.6f}",
                         "model": tri["model"],
                         "reduction_pct": tri["reduction_pct"],
                         "rounds": tri.get("rounds", 1),
                         "sufficient": tri.get("sufficient", True)},
                    )
                    # Live economics: price the tokens triage kept out of the deep model.
                    saved = cost_meter.triage_saved(tri["full_tokens"], tri["focused_tokens"], DEEP_COST_PER_1K)
                    yield _sse(
                        "cost",
                        (f"💸 Triage saved ~${saved['triage_saved_usd']:.4f} this query — "
                         f"{saved['reduction_pct']}% fewer tokens to the deep model "
                         f"({saved['saved_tokens']:,} tok)"),
                        {"saved_usd": round(saved["triage_saved_usd"], 6),
                         "reduction_pct": saved["reduction_pct"]},
                    )

            async for event in run_agent(question, primary_path, agent_context, backend, routing):
                data = event.replace("data: ", "", 1).strip()
                try:
                    parsed = json.loads(data)
                    audit.record(sid, parsed.get("step", "?"), parsed)  # persist agent steps
                except Exception:
                    pass
                yield {"data": data}

        except Exception as e:
            audit.record(sid, "error", {"content": str(e)})
            yield {"data": json.dumps({"step": "error", "content": str(e)})}

    return EventSourceResponse(event_stream())


@app.post("/cuda-to-rocm")
async def cuda_to_rocm_direct(payload: dict, _=Depends(require_auth)):
    """Direct CUDA → ROCm conversion without repo fetch (offline, no keys needed)."""
    from tools import migrate_cuda_to_rocm
    cuda_code = payload.get("code", "")
    if not cuda_code:
        raise HTTPException(400, "No code provided")
    result = migrate_cuda_to_rocm(cuda_code)
    return {"result": result}
