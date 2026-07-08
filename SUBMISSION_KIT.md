# REPOMIND v3 — Submission Kit (lablab.ai Track 3)

## Cover image
`slides/cover.png` (1200×630 @2x). Ready to upload.

## Project Title
**REPOMIND v3 — The On-Premises AI Coding Agent for Enterprises That Banned Copilot**

## Short Description (≤ ~180 chars)
On-prem AI code intelligence on AMD MI300X: 256K-context reasoning, Gemma-triage, CUDA→ROCm migration, air-gapped, with an Ed25519-signed audit trail. Built for compliance-locked enterprises.

## Long Description
Apple, JP Morgan and Goldman restricted cloud AI coding tools for compliance reasons — yet their engineers still ship code daily. REPOMIND v3 is what they deploy instead: an on-premises coding agent that runs entirely inside the firewall on **AMD MI300X**, so no source ever leaves the building.

**How it uses AMD platforms (meaningfully, all three):**
- **AMD Instinct MI300X (via AMD Developer Cloud):** the deep-analysis pass runs a real coding model at 256K context on a single MI300X — 77 GiB weights + a 94 GiB KV pool that a single NVIDIA H100 80GB cannot hold. Verified in ACT I ($4.12 / 124 min, Zenodo DOI 10.5281/zenodo.20330468).
- **ROCm:** a CUDA→ROCm migration agent (39 API rules + kernel-launch rewrite → `hipLaunchKernelGGL`) emits a `git apply`-clean patch — a direct on-ramp into the ROCm ecosystem.
- **Fireworks AI (AMD-hardware-hosted Gemma 27B):** Gemma is **load-bearing** — on deep queries it triages the file manifest and selects the relevant subset (measured token reduction), so the MI300X pass isn't fed the whole repo. (Eligible for *Best AMD-Hosted Gemma Project*.)

**What makes it complete:** containerized (`docker compose up`), runs fully offline with no GPU/keys (`make demo-offline`), 28 passing tests, enforced air-gap mode (external egress hard-refused), API auth, path-sandboxed tools, and a **tamper-evident, SHA-256 hash-chained AND Ed25519-signed audit log** aligned to EU AI Act Article 12.

**The startup vision:** the on-prem AI-infra company for the compliance-locked segment — a wedge (air-gap + MI300X + CUDA→ROCm) into an underserved market with a regulatory tailwind. Built solo by an AMD ACT I winner.

MIT-licensed core. Reproducible. Open source: github.com/SRKRZ23/repomind-v3

## Technology / Category Tags
`AMD MI300X` · `ROCm` · `Fireworks AI` · `Gemma` · `AI Agent` · `On-Prem / Air-Gapped` · `Enterprise` · `Code Intelligence` · `CUDA→ROCm` · `Compliance / EU AI Act` · `Docker`

## Demo Application URL
Deploy after kickoff (credits): Vercel frontend → AMD Developer Cloud backend. Fallback that always works: hosted `make demo-offline` (mock vLLM) so the URL runs the full SC-TIR loop with no GPU/keys.

---

## 3-MINUTE VIDEO SCRIPT (timecoded, mapped to the 4 official criteria)
_Judges watch this. Order = hook → novelty → completeness → AMD → vision. Screen-record the live app; voice-over._

**0:00–0:20 — HOOK (Creativity/Market).**
"Apple banned Copilot. JP Morgan banned Cursor. Their engineers still write code every day — with no compliant tool. REPOMIND is what they deploy instead: an AI coding agent that runs on-premises, on AMD, so no code ever leaves the building." — show the cover + the one-line problem.

**0:20–1:05 — THE NOVEL BEHAVIOR (Creativity + Use of AMD + Gemma bonus).**
Live: paste a GitHub repo + a question. Show the live SC-TIR trace. When it routes deep: "Here's the part that's new — **Gemma 27B, AMD-hosted on Fireworks, triages the codebase first**: it reads the file manifest, picks the relevant files, and hands the AMD MI300X a focused context." → point to the on-screen **"Gemma selected N files → X% context reduction"** event. "The cheap model does the context engineering the expensive 256K pass would otherwise waste."

**1:05–1:45 — COMPLETENESS + AMD depth.**
- "The deep pass runs a real coding model at **256K context on a single MI300X** — 77 GiB weights + a 94 GiB KV pool a single H100 can't hold." (show the hardware slide / an AMD Dev Cloud run).
- Switch to **CUDA→ROCm mode**: paste a CUDA kernel → show the `hipLaunchKernelGGL` diff → "and it's `git apply`-clean." (a direct ROCm on-ramp).
- "It's containerized, it has 28 passing tests, and it runs **fully offline with no GPU and no keys** — `make demo-offline`." (show tests green).

**1:45–2:20 — COMPLIANCE / TRUST (Completeness).**
- Toggle **AIR_GAP=1**: "In air-gap mode the external path is hard-refused — provable zero egress." 
- Show the **compliance heuristic pre-scan** (honestly labeled) + the **Ed25519-signed, hash-chained audit log**: "Every step is signed and tamper-evident — third-party verifiable, aligned to EU AI Act Article 12." (run `verify_signatures`).

**2:20–2:50 — THE COMPANY (Product/Market).**
"This is the wedge into a real market: the compliance-locked enterprises that had to ban every cloud AI tool. On-prem + AMD MI300X + CUDA→ROCm is a combination no incumbent pairs. Built solo — ACT I winner, now ACT II product."

**2:50–3:00 — CLOSE.**
"REPOMIND v3. Runs on AMD MI300X, ROCm, and AMD-hosted Gemma. Open source. `docker compose up`." — repo URL + AMD/Gemma/Fireworks logos.

**Production notes:** screen-record at 1080p; keep the live app (not slides) on screen ≥60% of the time — judges reward *seeing it work*. Put the Gemma-triage event and the ROCm diff on screen clearly (they map to the two prize criteria: Gemma bonus + Use of AMD).
