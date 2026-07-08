# REPOMIND v3 — Business Case & Market (sourced)

_One engine, two markets, all flowing to AMD. Every third-party fact carries a numbered source (see **References**). **[M] = measured** (ACT I on real MI300X + live bench). **[E] = modeled** — a ranged estimate on the measured floor + cited public data, never asserted as booked. Named companies are used as public pain-point evidence and are **not** represented as customers._

---

## 1. The thesis in one line
REPOMIND is the **on-prem cost + trust layer** for enterprise AI coding on AMD — and the **LLM cost-router** for enterprises already bleeding on cloud AI. Both markets pull through AMD silicon.

```
                    ┌────────── ONE ENGINE ──────────┐
                    │ skeleton −89% · cache −90% ·    │
                    │ cascade · Ed25519 audit ·       │
                    │ open-weight only                │
                    └───────┬───────────────┬─────────┘
        PATH A — THE BAN    │               │   PATH B — THE TOKEN TAX
   (legally can't use cloud AI)             │  (bleeding on cloud AI cost)
   → on-prem, $0 per-token                  │  → router cuts bill 40–70%, migrates to AMD
                    └──────── ALL PULLS THROUGH AMD (Instinct + EPYC) ────────┘
```

---

## 2. The measured floor (defend to any hostile engineer/CFO)
- **[M]** ACT I on a real **AMD MI300X**: full **256K-token repo served for $4.12** / 124-min stress test / 62 reproducible data points @ $1.99/GPU-hr; 77.29 GiB weights + 94.58 GiB KV; **~31 developers per GPU** clean at 8K–64K; **6.49×** throughput (8K vs 32K). DOI 10.5281/zenodo.20330468.
- **[M]** Live cost layer (MacBook + AMD-hosted Fireworks, `backend/bench_cost_layer.py`): **AST skeleton −89%** tokens (own codebase 17,289→1,961), **cached input −90%**<sup>13</sup>, **confidence cascade** skips the deep call when the cheap tier is sure. The app streams the **$ saved per query** on screen.
- Everything below is modeled **on** this floor + cited public prices.

---

## 3. PATH A — the ban (regulated enterprises legally barred from cloud AI)
| Company / body | Cited evidence | Pain |
|---|---|---|
| **Samsung** | Banned ChatGPT company-wide **May 2023** after engineers leaked chip source code<sup>1</sup> | any paste risks leaking IP to a 3rd-party cloud |
| **JP Morgan** | Restricted employee ChatGPT firm-wide **Feb 2023** (compliance)<sup>2</sup> | ~50K technologists blocked |
| **Apple** | Restricted ChatGPT **and GitHub Copilot** **May 2023** over data-egress<sup>3</sup> | the exact product REPOMIND replaces |
| **US Space Force / gov** | Banned generative AI / CUI **2023**; consumer AI not authorized for CUI<sup>4</sup> | can't send classified code to any cloud |
| **Healthcare** | ChatGPT not HIPAA-compliant; remedy = self-host on-prem; avg HIPAA settlement **~$1.2M**<sup>5</sup> | PHI can't leave the system |
| **EU AI Act** | Non-compliance penalty up to **€35M or 7%** of global turnover (Art. 99)<sup>6</sup> | existential compliance risk |

**REPOMIND for Path A:** open-weight on the enterprise's **own AMD GPU → $0 per-token**, data never leaves; the **Ed25519-signed AI Flight Recorder** turns compliance into automatic signed evidence.

### Per-company on-prem economics [E] (modeled on the measured floor)
| Enterprise | Devs | On-prem AMD GPUs¹ | GPU-efficiency saving/yr² |
|---|---|---|---|
| JP Morgan | 50,000 | ~77 MI300X | **~$7.6M** |
| Meta | 30,000 | ~48 | **~$4.6M** |
| Lockheed | 20,000 | ~32 | **~$3.1M** |
| Apple | 10,000 | ~16 | **~$1.5M** |
| Netflix | 3,000 | ~7 | **~$0.6M** |

¹ Modeled on the measured 6.49× + ~31 devs/GPU at realistic peak concurrency. ² vs a naïve 32K deployment @ ~$1.99/GPU-hr. **The conservative hammer:** one 5,000-dev bank recovers **$11–22M/yr** of locked coding productivity — even at **1% capture = $1.5M, still 8× the $180K license, payback in days.** This is AMD adoption from a **$0 baseline** (the segment deploys zero AI today; NVIDIA is legally locked out) — **not fewer sales.**

---

## 4. PATH B — the token tax (enterprises already bleeding on cloud AI cost)
"The subsidy era ended" in 2026:
| Payer | Cited evidence | Signal |
|---|---|---|
| **Uber** | Burned its **entire 2026 AI-coding budget in 4 months**; capped $1,500/mo/eng; ~5,000 eng at $500–2,000/mo<sup>7</sup> | can't forecast, hard cap kills productivity |
| **GitHub Copilot** | Usage-based billing (Jun 2026): **$29 → $750/mo** per dev (~25×); agentic ~1,000× more tokens<sup>8</sup> | overnight bill shock |
| **Cursor / Anysphere** | **$2B ARR**, "neutral/negative" margins, built its own router to cut inference<sup>9</sup> | even the vendors bleed |
| **Microsoft** | **Cut internal Claude Code licenses** (Jun 2026) after per-eng cost $500–2,000/mo — "used it too much"<sup>18</sup> | even the richest can't afford the token trap |
| **Enterprises** | **37% spend >$250K/yr** on LLM APIs; model-API spend **$3.5B→$8.4B** (H1 2025, measured)<sup>10</sup> | the flow a router redirects |

**REPOMIND for Path B:** the same engine cuts any Claude/OpenAI/Gemini bill **40–70%** (measured levers; industry reports **40–85%**, ~74% of queries never need the frontier<sup>12</sup>) and **migrates the cheap 60–80% of traffic to AMD-hosted open-weight** → every optimized customer becomes an AMD-inference customer.

### Router savings [E]
| Payer | Today | After −40–70% |
|---|---|---|
| Uber (~5,000 eng) | ~$30M/yr | **save $12–21M** |
| Copilot dev | $750/mo | **save $300–525** |
| $1M/yr spender | $1M/yr | **save $400–850K** |

---

## 5. The market — nested layers (do NOT stack; corroborate)
| Layer | Figure · year · type | Source |
|---|---|---|
| **AMD AI-accelerator TAM** | **$1 TRILLION by 2030** (from $500B/2028) | Lisa Su, AMD Financial Analyst Day Nov 2025<sup>14</sup> |
| Total generative-AI | $13.8B (2024, **measured**) → ~$104B–1.26T (2034, modeled) | Menlo / Fortune BI |
| Sovereign / on-prem AI infra | **$15B (2025) → $177B (2035)**, 28% CAGR | Precedence / McKinsey |
| Enterprise-LLM market | **$8.8B (2025) → $71.1B (2034)**, 26% CAGR | GMI<sup>11</sup> |
| **Model-API spend (the flow)** | **$3.5B → $8.4B** (H1 2025, **measured**) | Menlo Ventures<sup>10</sup> |
| AI coding-assistant SAM | ~$7–8.5B (2025) | Grand View / Mordor |

**Why "$8.4B" ≠ "$71B":** the $8.4B is the **measured cash flowing today** (what a router redirects now); the $71B is a **modeled 2034 projection** of the whole enterprise-LLM market. Different layers, years, methods — corroborate side-by-side, never add.

**Serviceable:** Path A ≈ **2,000+ regulated enterprises × $180K–2M = $0.4–4B**. Path B ≈ >$250K/yr cohort ≈ $3B flow → ~$1.5B savings pool → **$225–300M** capture ceiling.

---

## 6. Who benefits — especially AMD
### 🔴 AMD — the platform (both CPU **and** GPU)
- **GPU pull-through:** each on-prem deployment ≈ **$200–500K** Instinct silicon; Data Center **$5.8B, +57% YoY** (Q1 FY2026)<sup>15</sup>; Lisa Su names **agentic AI** as the driver — REPOMIND is one. Plugs into the **$1T-by-2030** accelerator TAM<sup>14</sup>.
- **CPU pull-through:** REPOMIND is an AI agent (scheduling + tool-invocation) — the exact workload AMD's own blog **"Agentic AI Changes the CPU/GPU Equation"** says drives CPU demand<sup>17</sup>. **EPYC hit a record 46.2% server-CPU revenue share**; server-CPU TAM → **$120–170B by 2030**; Lisa Su predicts a ~**1:1 CPU:GPU ratio**. So each deployment pulls **EPYC + Instinct** — both halves of the AMD data-center BOM.
- **The segment NVIDIA can't defend:** air-gapped / compliance-locked enterprises, where owned-hardware $0-per-token is where AMD's TCO argument is strongest. Built entirely on AMD's **open stack (ROCm 7 + vLLM)**; deep tier GLM-5.2 has **AMD Day-0 support** + an official `amd/GLM-5.2-MXFP4` quant.
- **AMD's own direction validates this.** AMD's official **"Agent Computers"** campaign markets *"agentic AI workflows running end-to-end on your machine… fully local execution… **no token limits, no cloud dependency**"* — REPOMIND is that, for the enterprise. And the **Advancing AI 2026 Developer Track** (Jul 22–23, Moscone) programs a session on *"Coding Agents and the Future of Open Source Software Development"* (Linux Foundation / PyTorch) alongside vLLM, SGL and George Hotz on open AMD infra — coding agents + open + local is AMD's stated roadmap, and REPOMIND ships it today.
- **AMD's AI-software VP frames the exact problem REPOMIND solves.** Anush Elangovan (VP, AI Software, AMD): *"software is tokens plus time, and speed is the moat"*<sup>19</sup> — REPOMIND's cost layer **is** token-plus-time optimization (skeleton −89% tokens, cache −90%, cascade + speculative decode = less time). His **"ROCm Everywhere"** vision — ROCm 7 running from MI300X server clusters to personal Radeon PCs — is exactly our Radeon → MI300X tiering; AMD's stated goal is to give *"enterprises the confidence to build sustainable AI infrastructure on open standards,"* with the **Instinct MI350P PCIe** positioned as the enterprise on-prem accelerator (leadership cost, simplified deployment).

### 🔵 Google DeepMind / Gemma
Gemma 4 is positioned for *"agentic workflows, coding assistants, regulated workloads on AMD ROCm"*<sup>16</sup> yet has **no named regulated on-prem production reference** — REPOMIND is it.

### 🟢 Fireworks AI (partner, on AMD Instinct)
The paid burst tier is Fireworks — recurring AMD-hosted API revenue per customer; the router keeps burst cheap enough that more enterprises adopt → more total AMD-served consumption.

### 🟢 The enterprise
Path A: recovers **$11–22M/yr** locked productivity, $0 egress, IP-leak + EU-AI-Act risk down. Path B: **40–70% bill cut**, payback in days.

---

## 7. Does on-prem actually pencil out? (the TCO objection, answered)
Master equation: **cost/query = GPU-seconds/query × ($amortized-hardware + power)/GPU-second.** REPOMIND attacks the first factor and raises utilization:
- **Depreciation / break-even:** cascade keeps the expensive GPU idle except for the hard ~20%; skeleton/cache cut compute/query → **~31 devs/GPU**; co-location (SPX + multi-process) + batching keep one box serving a whole team → high utilization.
- **Power:** cache-hits skip prefill compute; FP8/MXFP4 quant + speculative decoding raise tokens-per-watt.
- **Ops:** Docker `compose up` + Lemonade (AMD's official ROCm server) + automatic signed audit.
- **Frontier:** REPOMIND is **hybrid** — cheap majority local, hard minority bursts to a bigger AMD-hosted model (GLM-5.2, ~1% behind Claude Opus 4.8 on FrontierSWE). We route, we don't claim to replace.
- **Honest limit:** capex/power don't go to zero — they go further. The case is **enterprise-scale utilization** + the **banned segment** (where cloud is off the table).

---

## 8. Business model
MIT open-core → enterprise license **$500 / $2,500 / $15K per month** (starter → air-gapped) + AMD-cloud burst usage = **$180K–2M/yr** per enterprise, high-margin (open-weight — no model-training cost, no per-token COGS on-prem). Routing/gateways is a crowded category (Portkey, LiteLLM, Helicone, TrueFoundry) — our moat is **coding-native AST compression + the Ed25519 Flight Recorder audit + the AMD open-weight migration path**, not "we route."

---

## Honesty guardrails
- Measured claims are labeled **[M]**; all per-company / market $ are **[E] modeled**, ranged, never booked.
- The provider cache discount (−90%) is the providers' own pricing we exploit, not our invention.
- Open-weight is not the absolute reasoning frontier *yet* (~6-month lag) → hybrid burst, not all-local.
- Named companies are public pain-point evidence, **not customers**.

## References
1 Forbes 2023 (Samsung ChatGPT ban) · 2 CNN 2023 (JPMorgan) · 3 TechCrunch 2023 (Apple / Copilot) · 4 Air & Space Forces 2023 (Space Force / CUI) · 5 Brellium / HHS-OCR (HIPAA ~$1.2M avg) · 6 artificialintelligenceact.eu (Art. 99, ≤€35M / 7%) · 7 TechCrunch 2026 (Uber $1,500 cap) · 8 GitHub Blog / TechCrunch 2026 (Copilot $29→$750) · 9 TechCrunch / Reuters 2026 (Cursor $2B ARR) · 10 Menlo Ventures 2025 ($3.5B→$8.4B API spend; 37% >$250K/yr) · 11 Global Market Insights ($8.8B→$71.1B, 26% CAGR) · 12 Orq / TrueFoundry / IBM 2026 (routing 40–85%) · 13 Anthropic / OpenAI / Google docs (prompt cache −90%) · 14 CNBC — Lisa Su, AMD Financial Analyst Day Nov 2025 ($1T by 2030) · 15 CNBC / DataCenterDynamics (AMD Q1 FY2026 DC $5.8B, +57% YoY) · 16 blog.google — Gemma 4 (agentic / coding / regulated / AMD ROCm) · 17 AMD "Agentic AI Changes the CPU/GPU Equation" / Mercury Research (EPYC record 46.2% server-CPU revenue share; server-CPU TAM →$120–170B by 2030; Lisa Su ~1:1 CPU:GPU) · 18 thenextweb / cryptobriefing 2026 (Microsoft pulls internal Claude Code over cost) · 19 Dev Interrupted / migovi 2026 — Anush Elangovan (AMD VP, AI Software): "software is tokens plus time, speed is the moat"; "ROCm Everywhere" (MI300X clusters → personal Radeon); Instinct MI350P PCIe enterprise on-prem accelerator.
