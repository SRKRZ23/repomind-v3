# REPOMIND v3

> The on-premises coding agent that fits a real production coding model + 256K context
> on a single AMD MI300X. Three steps to a runnable enterprise deployment.

**AMD Hackathon ACT II — Track 3 Unicorn | AMD ACT I Winner (1st Place AI Agents)**

📊 **Full sourced business case — two markets, per-company economics, the market stack, and who benefits (especially AMD): [BUSINESS_CASE.md](BUSINESS_CASE.md).**

---

## ✅ AMD Compute Usage (Track 3 requirement)

Every inference path in REPOMIND v3 runs on **AMD silicon** — directly on **AMD Instinct MI300X**
via **AMD Developer Cloud**, or on **AMD-hosted Fireworks AI**. There is no NVIDIA path — and
**no closed models**: every model is open-weight (Gemma, GLM, Qwen3-Coder), served on AMD. No
OpenAI / Anthropic / Gemini anywhere in the product.

> **Fireworks AI serves on AMD hardware**, so **every model call in REPOMIND is AMD compute** — the
> AMD-usage requirement is satisfied by the Fireworks path alone (confirmed by the AMD/lablab
> organizers: "showcase AMD resources for the LLM component (Fireworks)"). MI300X / Radeon is the
> on-prem deployment story layered on top.

> **The models we use are AMD-first-class, not just AMD-hosted.** The deep/burst tier **GLM 5.2** has
> **AMD Day-0 support** — FP8 serving, tool calling, reasoning parsing, and MTP speculative decoding on
> **AMD Instinct via ROCm + AITER** — and AMD ships an official [`amd/GLM-5.2-MXFP4`](https://huggingface.co/amd/GLM-5.2-MXFP4)
> quantization targeting MI350/MI355 + ROCm 7.0+. Gemma likewise has Day-0 AMD support. So the on-prem
> deep tier can be self-hosted on AMD Instinct, not only reached via Fireworks. REPOMIND hardcodes no
> tensor-parallel size — the deep tier is reached via `VLLM_BASE_URL`, so serving topology is a deploy-time
> choice. *(AMD-recommended recipe: **`GLM-5.2-FP8` serves fine at TP=8** on an 8×MI350X box with AITER —
> `vllm serve zai-org/GLM-5.2-FP8 --kv-cache-dtype fp8_e4m3 --tensor-parallel-size 8 --linear-backend aiter
> --moe-backend aiter`, scalable toward 1M context; the **MXFP4** variant's sparse-MLA kernel needs
> ≥16 heads/card, so run that one at **TP=4**.)*

| Tier | Runs on | Where in code |
|---|---|---|
| **Deep reasoning** (≥8K ctx) | **AMD Instinct MI300X** · vLLM on **ROCm** · Qwen3-Coder-Next-FP8 (80B/3B MoE) · 256K (`--max-model-len 262144`) | `backend/vllm_client.py` (`VLLM_BASE_URL` → MI300X endpoint), `backend/router.py` |
| **Gemma triage** (file selection) | **Gemma 27B on AMD-hosted Fireworks AI** | `backend/triage.py`, `backend/fireworks_client.py` |
| **Air-gapped** (`AIR_GAP=1`) | **100% on-prem AMD MI300X** — Fireworks path hard-refused at the client | `backend/router.py`, `backend/fireworks_client.py` |

**Verified on a real AMD MI300X (ACT I):** 77.29 GiB weights + 94.58 GiB KV cache, 176.0 / 191.7 GiB
peak (92%), 256K confirmed via `/v1/models`, **124-min stress test, $4.12 total, 62 reproducible
data points** (@ $1.99/GPU-hr). Full logs + preprint: **DOI [10.5281/zenodo.20330468](https://doi.org/10.5281/zenodo.20330468)**.
A single NVIDIA H100 80 GB cannot hold weights + 256K KV + activations at this config — this is an
AMD-192 GB-per-card workload by construction.

## 🆕 New in v3 (built for ACT II — distinct from the ACT I repo)

REPOMIND v3 is a **new codebase** for the Unicorn track, not a re-submission of ACT I. New work:
**Gemma load-bearing triage** (`triage.py`) · **Ed25519-signed + SHA-256 hash-chained tamper-evident
audit log** with key-pinning (`audit.py`) · **API auth** (constant-time) · **enforced air-gap egress
refusal** · **CUDA→ROCm migration agent** (39 rules + kernel-launch rewrite → `git apply`-clean diff)
· **path-sandboxed tools** · **agent self-recovery** · **measured cost layer** (prompt caching + AST skeleton + confidence cascade) · **38 pytest tests** · **Docker + CI** ·
**`make demo-offline`** (runs with no GPU/keys). ACT I contributed only the verified MI300X benchmark
numbers cited above.

---

## Why REPOMIND v3

Several large regulated employers have restricted cloud AI coding assistants for their
engineers (per public reporting: JP Morgan restricted generative-AI coding tools; Apple
restricted external AI coding assistants; Goldman's CIO has spoken publicly about immature
AI governance). These orgs still write code every day — and need a tool that runs inside
their own perimeter.

REPOMIND v3 is built for that gap: on-premises, auditable, AMD MI300X-powered.

| Company (public reporting) | Reported constraint | REPOMIND answer |
|---|---|---|
| JP Morgan (~50K devs) | Restricted generative-AI coding tools | On-prem Docker deploy |
| Apple (30K+ engineers) | Restricted external AI coding assistants | Enforced air-gap mode (AIR_GAP=1) |
| Goldman / EU enterprises | Immature AI governance / EU AI Act | Heuristic pre-scan + audit-trail indicator |

> We do **not** claim these companies are customers. They are illustrative of the
> compliance-locked segment. See slide deck for sourcing notes.

---

## Quickstart

```bash
git clone https://github.com/SRKRZ23/repomind-v3 && cd repomind-v3
cp .env.example .env            # add FIREWORKS_API_KEY, or run fully offline (below)
docker compose up --build
```

Open http://localhost:3000

> **Portable build:** base images (`python:3.11-slim`, `node:20-alpine`, `nginx:alpine`) are multi-arch, so `docker compose up --build` compiles **natively on `linux/amd64`** — no emulation, no arch mismatch. The `FIREWORKS_API_KEY` is read from the environment and is **never** baked into the image (`.env` is git- and docker-ignored).

**Run it with NO GPU and NO API keys** (full SC-TIR loop against a mock vLLM):

```bash
make demo-offline               # docker compose --profile mock up, AIR_GAP=1
```

---

## Features

### 🔀 Smart Routing + Gemma Triage (with enforced air-gap option)
- **< 8K tokens** → Gemma 27B via Fireworks AI (fast first-pass tier, ~$0.001/query, ~2s)
- **≥ 8K tokens** → **Gemma triage** reads a compact file manifest + your question and selects the
  relevant files (measured token reduction), then **AMD MI300X** · Qwen3-Coder-Next-FP8 · 256K
  reasons deeply over that focused subset (~$0.008–$0.05+ per deep query, scales with context).
  This makes Gemma load-bearing — real work the big model would otherwise waste 256K compute on.
- **`AIR_GAP=1`** → **enforced** on-prem: every query goes to MI300X, triage is skipped, and the
  external Fireworks path is *hard-refused at the client* (not just routed around). Real zero-egress.
- **On-prem local tier (deploy target):** the Gemma router runs on the customer's own AMD GPU (e.g. a
  48 GB Radeon) served via **Lemonade** — AMD's official local-AI server (llama.cpp + native ROCm/NPU,
  bundles ROCm 7.12) — optionally accelerated with a **DFlash draft model for Gemma 4** (merged upstream
  in llama.cpp) on a single card. Fully open-weight, AMD-native, zero per-token cost.

### 🔐 API auth
Set `API_KEY` to require `Authorization: Bearer <key>` (or `X-API-Key`) on `/analyze` and
`/cuda-to-rocm`. Unset = open local-demo mode (surfaced in `/health`).

### 🔍 Codebase Analysis
Multi-repo context. The SC-TIR agent loop (PLAN→CALL→OBSERVE→THINK→ANSWER) streams every
step live. Tool calls (read_file/grep/list_files/git_log) are scoped to the primary repo.

### ⚡ CUDA → ROCm Migration
Pattern-based migration: 39 API-mapping rules across memory/stream/event/device/error +
common math-library headers, **plus kernel-launch rewrite** (`kernel<<<grid,block>>>(...)`
→ `hipLaunchKernelGGL(...)`). Emits an **appliable unified diff** (`git apply`-clean).
Unit-tested against `demo/cuda_sample.cu`. Custom kernels, cuBLAS/cuDNN call signatures,
Thrust, warp intrinsics and PTX are out of scope (roadmap: AI-guided migration). This
complements — it does not replace — AMD's HIPIFY.

### 🔒 Security / Compliance Heuristic Pre-Scan
A fast **heuristic pre-scan** (NOT a certified control): word-boundary detection across
5 OWASP-LLM risk surfaces + an EU AI Act Article 12 record-keeping *indicator*, with real
`file:line` citations. A clear result is **not** an assurance of security or compliance.
The audit trail is now **Ed25519-signed** (when a signing key is configured) on top of the
SHA-256 hash chain. `audit.verify_signatures(path, expected_pubkey=...)` verifies each record;
pass the operator's **pinned public key** for anti-forgery (a wholesale re-sign with an
attacker's key is then rejected). Without pinning it proves tamper-evidence, not authenticity —
so pin the key out-of-band (via `AUDIT_SIGNING_KEY` + a KMS/HSM in production). Shipped and tested.

### 📒 AI Flight Recorder (tamper-evident audit log)
Every analysis and every SC-TIR step is persisted to the **AI Flight Recorder** — an append-only,
**SHA-256 hash-chained** JSONL log (`audit.py`) — any edit/deletion of a prior record is detectable
(`verify_chain`), and any incident can be **replayed** from the recorded chain.
The sequence counter survives process restart (seeded from the file). This makes the EU AI
Act Article 12 record-keeping claim concrete, not ephemeral. Set `AUDIT_LOG` to a WORM path
in production (a persistent volume is mounted by default in `docker-compose.yml`).

---

## 💸 Cost layer — measured, not projected

REPOMIND ships three cost levers, each **measured live on a MacBook + Fireworks** (run
`python backend/bench_cost_layer.py`). They apply to different query patterns and are
honest about it — the deep pass always sees real code:

| Lever | Measured | How |
|---|---|---|
| **AST skeleton** (`code_skeleton.py`) | **−89% tokens** on exploration/code-search (17,289 → 1,961) | signatures + imports + docstrings, bodies → `...`; reversible (full file fetched for the deep pass) |
| **Prompt caching** (`cost_meter.py` + `fireworks_client.py`) | up to **100% of an ~18K repo prefix cached** on repeat; **cached input −90%** (GLM 5.2 published pricing) · faster warm TTFT | stable repo prefix first, `x-session-affinity`; output identical |
| **Confidence cascade** (`cascade.py`) | confident cheap answers **skip the deep call** entirely | token-margin / self-score gate, conservative (unsure → escalate) |

`cost_meter.savings_report()` emits a live headline (e.g. *"triage −89% … → $X saved this query"*)
from **actual provider usage**, so the demo shows economics that pencil out, on screen.
Backed by 10 cost-layer unit tests (38 total).

## Architecture

```
User → [React UI + live SSE agent trace]
         ↓
    [FastAPI backend]  →  route() by token count (or AIR_GAP → always MI300X)
         ├── < 8K → Gemma 27B (Fireworks AI)            [refused when AIR_GAP=1]
         └── ≥ 8K → AMD MI300X vLLM (Qwen3-Coder-Next-FP8, 256K ctx)
                          ↓
              [SC-TIR agent: PLAN→CALL→OBSERVE→THINK→ANSWER]
              Tools: read_file | grep_codebase | list_files | git_log
                   | migrate_cuda_to_rocm | compliance_scan
              (file tools are path-sandboxed to the repo)
```

## Why AMD MI300X (verified in ACT I)

Model: **Qwen/Qwen3-Coder-Next-FP8** — 80B total / 3B active (MoE), served on a single
MI300X at `--max-model-len 262144` (256K). Verified via rocm-smi + vLLM logs:

| Component | Verified |
|---|---|
| Model weights in VRAM | 77.29 GiB |
| KV cache memory available | 94.58 GiB |
| VRAM peak (post stress-test) | 176.0 / 191.7 GiB (92%) |
| `/v1/models` `max_model_len` | 262144 |

A single NVIDIA H100 80 GB cannot hold weights + 256K KV cache + activations at this
config (it exceeds 80 GB); matching MI300X's per-card memory needs multi-GPU sharding.
ACT I benchmark: 124 min stress test, $4.12 total, 62 reproducible data points.
Preprint: https://doi.org/10.5281/zenodo.20330468

---

## Tests

```bash
make test        # cd backend && python -m pytest -q   → 38 tests (unit + API integration + cost layer)
```

Covers CUDA→ROCm migration (incl. `cudaEventDestroy`, kernel-launch, and a real
`git apply --check`), compliance false-positive resistance, path-traversal rejection,
router thresholds, the parser, Gemma triage (selection + token reduction + fallback),
and API auth / bad-URL / streamed `/analyze` integration.

---

## Platform roadmap — the trust + cost layer for on-prem enterprise AI on AMD

REPOMIND is a focused product **and** the first tier of a platform. Every tier runs on the same
spine: **cheap local compute on AMD Radeon, bursting to AMD-hosted Fireworks only when it pays to.**

- **Tier 1 · Core (shipped, this repo):** on-prem coding agent on AMD (Radeon → MI300X) · Gemma-local → Fireworks cost routing · **AI Flight Recorder** · CUDA→ROCm · air-gap · compliance pre-scan.
- **Tier 2 · Trust & Governance (near-term):** Cost & Savings FinOps panel (live $ saved) · self-verifying answers · PII redaction gateway · continuous on-prem red-team · sovereign RAG.
- **Tier 3 · Sovereign & Regulated (horizon):** sovereign AI-in-a-box for regulators · verifiable unlearning (GDPR Art. 17) · AI-decision insurance · carbon+cost-aware routing · trusted AI metering.

> Tier 1 is shipped and tested. Tiers 2–3 are roadmap, not claims.

## AMD Hackathon ACT II

Built by Sardor Razikov — solo researcher, Tashkent, Uzbekistan.
ACT I: 1st Place AI Agents + Outstanding Social Engagement. Prize: AMD Radeon™ AI PRO R9700.

MIT-licensed core. Reproducible. Open source.
