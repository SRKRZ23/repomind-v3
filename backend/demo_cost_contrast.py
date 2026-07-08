#!/usr/bin/env python3
"""
REPOMIND — Token-Waste vs REPOMIND (measured cost contrast).

A camera-friendly, one-command demo for the pitch video. It shows, side by side,
what a naive agent spends vs what REPOMIND spends over a coding session — using
this repo's OWN files as the context.

HONESTY:
  • The per-query levers are MEASURED live: the AST-skeleton reduction is computed
    on this repo right now; the prompt-cache discount is the provider's own price.
  • The session shape (how many queries, how many the confidence-cascade resolves
    cheaply) is an ILLUSTRATIVE mix — clearly labelled [modeled].
Run:  cd backend && python demo_cost_contrast.py
"""
import os, glob, pathlib

# --- pricing (real GLM 5.2 on AMD-hosted Fireworks; from .env) ---
try:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass
IN   = float(os.getenv("FIREWORKS_COST_PER_1K_INPUT",  "0.0014"))   # $/1k input tok
OUT  = float(os.getenv("FIREWORKS_COST_PER_1K_OUTPUT", "0.0044"))   # $/1k output tok
CACHE_DISC = float(os.getenv("FIREWORKS_CACHE_DISCOUNT", "0.10"))   # cached read = 10% of input price (−90%)

import cost_meter, code_skeleton

# --- token counter (tiktoken if present, else chars/4) ---
try:
    import tiktoken; _enc = tiktoken.get_encoding("cl100k_base"); tok = lambda s: len(_enc.encode(s))
    TOKMODE = "tiktoken cl100k_base"
except Exception:
    tok = lambda s: len(s) // 4; TOKMODE = "chars/4 estimate"

R, G, B, DIM, END = "\033[91m", "\033[92m", "\033[1m", "\033[2m", "\033[0m"
def money(x): return f"${x:,.4f}"

# ── STEP 1 · MEASURED: pack this repo, then skeletonize it ──────────────
files = sorted(glob.glob("*.py"))[:12]
packed = ""
for f in files:
    try: packed += f"\n# FILE: {f}\n" + pathlib.Path(f).read_text(errors="ignore")
    except Exception: pass
CTX      = tok(packed)
skel     = code_skeleton.compress_repo_context(packed) if hasattr(code_skeleton, "compress_repo_context") else "\n".join(code_skeleton.skeletonize(packed).splitlines())
CTX_SKEL = max(1, tok(skel))
skel_cut = 100 * (1 - CTX_SKEL / CTX)

# ── STEP 2 · a coding session over this repo ────────────────────────────
QUERIES   = 10            # [modeled] queries in one session
OUT_TOK   = 500           # [modeled] avg answer length
CASCADE_SKIP = 4          # [modeled] queries the cheap local tier resolves → deep model skipped ($0 on-prem)
deep      = QUERIES - CASCADE_SKIP

# NAIVE agent: full repo context to the deep model on EVERY query, no caching
naive_in  = QUERIES * CTX
naive_out = QUERIES * OUT_TOK
naive     = cost_meter.call_cost(naive_in, naive_out, 0, IN, OUT, 0.0)["actual_usd"]

# REPOMIND: skeleton context + prompt-cache the repeated prefix + cascade skips the easy ones
rm_in     = deep * CTX_SKEL
rm_cached = max(0, deep - 1) * CTX_SKEL        # first call warms the cache; the rest read it at −90%
rm_out    = deep * OUT_TOK
rm        = cost_meter.call_cost(rm_in, rm_out, rm_cached, IN, OUT, CACHE_DISC)["actual_usd"]

saved     = naive - rm
pct       = 100 * saved / naive if naive else 0

def row(label, a, b): print(f"  {label:<26}{R}{a:>14}{END}   {G}{b:>14}{END}")

print(f"""
{B}════════════════════════════════════════════════════════════════{END}
{B}  REPOMIND — TOKEN WASTE  vs  REPOMIND   (measured cost contrast){END}
{B}════════════════════════════════════════════════════════════════{END}
{DIM}  context = this repo's own files ({len(files)} files) · tokens via {TOKMODE}
  pricing = GLM 5.2 on AMD-hosted Fireworks (${IN}/1k in · ${OUT}/1k out · cache −{int((1-CACHE_DISC)*100)}%){END}

{B}STEP 1 · MEASURED — skeletonize the repo context (live, right now){END}
  Full repo context .......... {R}{CTX:>8,}{END} tokens
  AST skeleton ............... {G}{CTX_SKEL:>8,}{END} tokens
  {B}→ −{skel_cut:.1f}%{END}  measured on this repo

{B}STEP 2 · one {QUERIES}-query coding session over this repo{END}  {DIM}[per-query levers measured; session mix modeled]{END}

  {'':<26}{R}{'NAIVE AGENT':>14}{END}   {G}{'REPOMIND':>14}{END}""")
row("Deep-model calls", QUERIES, f"{deep}  (−{CASCADE_SKIP} cascade)")
row("Input tokens billed", f"{naive_in:,}", f"{rm_in - rm_cached:,}")
row("  of which cached −90%", "0", f"{rm_cached:,}")
row("Output tokens", f"{naive_out:,}", f"{rm_out:,}")
print(f"  {'─'*56}")
row("Cost (this session)", money(naive), money(rm))
print(f"\n  {B}→ SAVED {G}{money(saved)}{END}  =  {B}{G}−{pct:.1f}%{END}  per session\n")

# ── STEP 3 · extrapolation (clearly modeled) ────────────────────────────
per_dev_mo = saved * 50          # [modeled] ~50 sessions/dev/month
ent_yr     = per_dev_mo * 12 * 5000
print(f"{B}STEP 3 · extrapolated{END} {DIM}[modeled]{END}")
print(f"  1 dev · ~50 sessions/mo ....... save {G}{money(per_dev_mo)}/mo{END}")
print(f"  5,000-dev enterprise .......... save {G}${ent_yr/1e6:,.1f}M/yr{END}")
print(f"\n{DIM}  On-prem, the cheap tier runs on the customer's own AMD GPU = $0 per-token.\n"
      f"  Per-query levers are measured; session mix + extrapolation are modeled, ranged.{END}\n")
