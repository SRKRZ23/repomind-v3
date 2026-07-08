"""
REPOMIND v3 tool implementations.
Each tool returns a string result for the agent's OBSERVE step.

Security note: read_file / list_files / grep_codebase are hardened against
path traversal — every resolved path is confined to the target repo. The agent
ingests UNTRUSTED repositories, so tool arguments (which an LLM may derive from
attacker-controlled repo content) must never escape the sandbox.
"""
import re
import difflib
import subprocess
from pathlib import Path


def _safe_target(repo_path: Path, user_path: str) -> Path | None:
    """Resolve user_path inside repo_path; return None if it escapes the sandbox."""
    repo_root = repo_path.resolve()
    try:
        resolved = (repo_root / user_path).resolve()
    except (OSError, ValueError):
        return None
    if resolved == repo_root or repo_root in resolved.parents:
        return resolved
    return None


def read_file(repo_path: Path, filepath: str, lines: str = None) -> str:
    target = _safe_target(repo_path, filepath)
    if target is None:
        return f"ERROR: path '{filepath}' is outside the repository sandbox (rejected)"
    if not target.exists() or not target.is_file():
        return f"ERROR: {filepath} not found"
    content = target.read_text(encoding="utf-8", errors="ignore")
    if lines:
        m = re.match(r"(\d+)-(\d+)", lines)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            content_lines = content.splitlines()
            content = "\n".join(content_lines[lo - 1:hi])
    return content[:8000]  # cap per read


def grep_codebase(repo_path: Path, pattern: str, path_filter: str = None) -> str:
    search_root = repo_path.resolve()
    if path_filter:
        safe = _safe_target(repo_path, path_filter)
        if safe is None:
            return f"ERROR: path_filter '{path_filter}' is outside the repository sandbox (rejected)"
        search_root = safe
    # "--" terminates option parsing so a pattern beginning with "-" isn't read as a flag.
    cmd = ["grep", "-rn", "--include=*.py", "--include=*.ts", "--include=*.js",
           "--include=*.go", "--include=*.rs", "--include=*.cpp", "--include=*.cu",
           "--include=*.h", "-m", "50", "--", pattern, str(search_root)]
    if path_filter:
        cmd = ["grep", "-rn", "-m", "50", "--", pattern, str(search_root)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = result.stdout.strip()
        return out[:6000] if out else f"No matches for '{pattern}'"
    except subprocess.TimeoutExpired:
        return "grep timed out"
    except Exception as e:
        return f"grep error: {e}"


def list_files(repo_path: Path, subdir: str = "") -> str:
    target = _safe_target(repo_path, subdir) if subdir else repo_path.resolve()
    if target is None:
        return f"ERROR: path '{subdir}' is outside the repository sandbox (rejected)"
    if not target.exists():
        return f"ERROR: {subdir} not found"
    files = []
    for f in sorted(target.rglob("*")):
        if f.is_file() and ".git" not in str(f):
            files.append(str(f.relative_to(repo_path.resolve())))
    return "\n".join(files[:200])


def git_log(repo_path: Path, n: int = 10) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log", f"-{n}",
             "--pretty=format:%h %ad %s", "--date=short"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or "No git history"
    except Exception as e:
        return f"git log error: {e}"


# ── CUDA → HIP/ROCm migration ────────────────────────────────────────────────
# Human-readable name + regex + replacement. Covers includes, memory, streams,
# events, device, and error APIs. Kernel-launch syntax (<<<>>>) is handled
# separately below because it requires argument reordering, and a partial set of
# math-library headers is mapped. NOT a full port: cuBLAS/cuDNN *call* rewrites,
# Thrust, warp intrinsics, and PTX are out of scope (see roadmap).
CUDA_TO_HIP = [
    ("#include <cuda.h>",            r"#include\s*<cuda\.h>",              "#include <hip/hip_runtime.h>"),
    ("#include <cuda_runtime.h>",    r"#include\s*<cuda_runtime\.h>",      "#include <hip/hip_runtime.h>"),
    ("#include <cuda_runtime_api.h>", r"#include\s*<cuda_runtime_api\.h>", "#include <hip/hip_runtime_api.h>"),
    ("#include <cublas_v2.h>",       r"#include\s*<cublas_v2\.h>",         "#include <hipblas/hipblas.h>"),
    ("#include <cublas.h>",          r"#include\s*<cublas\.h>",            "#include <hipblas/hipblas.h>"),
    ("#include <cudnn.h>",           r"#include\s*<cudnn\.h>",             "#include <miopen/miopen.h>"),
    ("cudaMalloc",                   r"\bcudaMalloc\b",                    "hipMalloc"),
    ("cudaMallocManaged",            r"\bcudaMallocManaged\b",             "hipMallocManaged"),
    ("cudaFree",                     r"\bcudaFree\b",                      "hipFree"),
    ("cudaHostAlloc",                r"\bcudaHostAlloc\b",                 "hipHostMalloc"),
    ("cudaFreeHost",                 r"\bcudaFreeHost\b",                  "hipHostFree"),
    ("cudaMemcpy",                   r"\bcudaMemcpy\b",                    "hipMemcpy"),
    ("cudaMemcpyAsync",              r"\bcudaMemcpyAsync\b",               "hipMemcpyAsync"),
    ("cudaMemcpyHostToDevice",       r"\bcudaMemcpyHostToDevice\b",        "hipMemcpyHostToDevice"),
    ("cudaMemcpyDeviceToHost",       r"\bcudaMemcpyDeviceToHost\b",        "hipMemcpyDeviceToHost"),
    ("cudaMemcpyDeviceToDevice",     r"\bcudaMemcpyDeviceToDevice\b",      "hipMemcpyDeviceToDevice"),
    ("cudaMemset",                   r"\bcudaMemset\b",                    "hipMemset"),
    ("cudaMemGetInfo",               r"\bcudaMemGetInfo\b",                "hipMemGetInfo"),
    ("cudaDeviceSynchronize",        r"\bcudaDeviceSynchronize\b",         "hipDeviceSynchronize"),
    ("cudaThreadSynchronize",        r"\bcudaThreadSynchronize\b",         "hipDeviceSynchronize"),
    ("cudaStreamSynchronize",        r"\bcudaStreamSynchronize\b",         "hipStreamSynchronize"),
    ("cudaGetLastError",             r"\bcudaGetLastError\b",              "hipGetLastError"),
    ("cudaGetErrorString",           r"\bcudaGetErrorString\b",            "hipGetErrorString"),
    ("cudaSuccess",                  r"\bcudaSuccess\b",                   "hipSuccess"),
    ("cudaError_t",                  r"\bcudaError_t\b",                   "hipError_t"),
    ("cudaStream_t",                 r"\bcudaStream_t\b",                  "hipStream_t"),
    ("cudaEvent_t",                  r"\bcudaEvent_t\b",                   "hipEvent_t"),
    ("cudaStreamCreate",             r"\bcudaStreamCreate\b",              "hipStreamCreate"),
    ("cudaStreamDestroy",            r"\bcudaStreamDestroy\b",             "hipStreamDestroy"),
    ("cudaEventCreate",              r"\bcudaEventCreate\b",               "hipEventCreate"),
    ("cudaEventRecord",              r"\bcudaEventRecord\b",               "hipEventRecord"),
    ("cudaEventSynchronize",         r"\bcudaEventSynchronize\b",          "hipEventSynchronize"),
    ("cudaEventElapsedTime",         r"\bcudaEventElapsedTime\b",          "hipEventElapsedTime"),
    ("cudaEventDestroy",             r"\bcudaEventDestroy\b",              "hipEventDestroy"),
    ("cudaSetDevice",                r"\bcudaSetDevice\b",                 "hipSetDevice"),
    ("cudaGetDevice",                r"\bcudaGetDevice\b",                 "hipGetDevice"),
    ("cudaGetDeviceCount",           r"\bcudaGetDeviceCount\b",            "hipGetDeviceCount"),
    ("cudaDeviceProp",               r"\bcudaDeviceProp\b",                "hipDeviceProp_t"),
    ("cudaGetDeviceProperties",      r"\bcudaGetDeviceProperties\b",       "hipGetDeviceProperties"),
]

# Kernel launch: name<<<grid, block[, shmem[, stream]]>>>(args)
#   → hipLaunchKernelGGL(name, grid, block, shmem, stream, args)
_KERNEL_LAUNCH_RE = re.compile(
    r"(\w+)\s*<<<\s*(.+?)\s*>>>\s*\((.*?)\)\s*;",
    re.DOTALL,
)


def _convert_kernel_launches(code: str) -> tuple[str, int]:
    count = 0

    def repl(m):
        nonlocal count
        name, cfg, args = m.group(1), m.group(2), m.group(3)
        # Split the <<< >>> config into up to 4 parts: grid, block, sharedMem, stream
        parts = [p.strip() for p in _split_top_level(cfg)]
        while len(parts) < 4:
            parts.append("0")
        grid, block, shmem, stream = parts[0], parts[1], parts[2], parts[3]
        args = args.strip()
        count += 1
        call = f"hipLaunchKernelGGL({name}, {grid}, {block}, {shmem}, {stream}"
        if args:
            call += f", {args}"
        return call + ");"

    return _KERNEL_LAUNCH_RE.sub(repl, code), count


def _split_top_level(s: str) -> list[str]:
    """Split on commas that are not nested inside (), [], or <>."""
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([<":
            depth += 1
        elif ch in ")]>":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def migrate_cuda_to_rocm(cuda_code: str) -> str:
    """Convert CUDA code to HIP/ROCm. Returns an appliable unified diff + summary."""
    original = cuda_code
    converted = cuda_code
    changes = []

    # 1. Kernel-launch syntax (must run before token swaps so <<<>>> is intact).
    converted, kl = _convert_kernel_launches(converted)
    if kl:
        changes.append(f"  kernel<<<grid,block>>>(...)  →  hipLaunchKernelGGL(...)   [{kl}×]")

    # 2. Token / include substitutions.
    for name, pattern, replacement in CUDA_TO_HIP:
        new_code, n = re.subn(pattern, replacement, converted)
        if n:
            changes.append(f"  {name}  →  {replacement}   [{n}×]")
            converted = new_code

    if not changes:
        return "No CUDA patterns detected. Code may already be ROCm-compatible."

    # 3. Real unified diff. SAME basename on both sides so `git apply --check` is clean
    #    (the target is renamed to *.hip.cpp on disk by the caller; noted in the summary).
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        converted.splitlines(keepends=True),
        fromfile="a/original.cu",
        tofile="b/original.cu",
        lineterm="\n",
    )
    diff_text = "".join(diff)

    # Summary trails AFTER a clear marker so callers can split the pure diff for git apply.
    summary = (
        f"\n{SUMMARY_MARKER}\n# {len(changes)} rule group(s) applied — rename target to *.hip.cpp:\n"
        + "\n".join(changes)
        + "\n# NOTE: pattern-based port (memory/stream/event/device/error APIs, kernel-launch,"
        + "\n#       math-library headers). Custom kernels, cuBLAS/cuDNN signatures, Thrust,"
        + "\n#       warp intrinsics and PTX still need manual review (roadmap: AI-guided)."
    )
    return diff_text + summary


SUMMARY_MARKER = "# ===== migration summary (not part of the patch) ====="


def split_patch(migration_output: str) -> str:
    """Return just the git-apply-clean unified diff, dropping the summary trailer."""
    return migration_output.split(SUMMARY_MARKER)[0].rstrip("\n") + "\n"


# ── Security / compliance heuristic pre-scan ─────────────────────────────────
# IMPORTANT: this is a fast HEURISTIC PRE-SCAN, not a certified security control.
# It uses word-boundary keyword matching to flag lines for human review. A "clear"
# result is NOT an assurance of security or regulatory compliance.
OWASP_LLM_CHECKS = [
    ("LLM01", "Prompt Injection (risky exec surfaces)",
     [r"\beval\s*\(", r"\bexec\s*\(", r"\bos\.system\b", r"\bos\.popen\b", r"\bsubprocess\."]),
    ("LLM02", "Insecure Output Handling",
     [r"\binnerHTML\b", r"\bdangerouslySetInnerHTML\b", r"document\.write\s*\("]),
    ("LLM06", "Sensitive Information Disclosure (possible hardcoded secret)",
     [r"\b(api[_-]?key|secret|password|passwd|private[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"][^'\"]{6,}",
      r"\b(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,})\b"]),
    ("LLM07", "Insecure Plugin / Unvalidated Outbound Call",
     [r"requests\.get\s*\(", r"urllib\.request\.urlopen\s*\(", r"\bfetch\s*\("]),
    ("LLM10", "Model Theft (untrusted deserialization)",
     [r"\bpickle\.load\b", r"\btorch\.load\b", r"\bjoblib\.load\b", r"\byaml\.load\s*\("]),
]

# Real logging / audit-trail indicators (word-boundary API calls, not substrings).
_LOGGING_RE = re.compile(
    r"(?:\bimport\s+logging\b|\blogging\.(?:info|debug|warning|error|getLogger)\b"
    r"|\blogger\.\w+\s*\(|\blog4j\b|\bwinston\b|\bslf4j\b|\baudit_log\s*\(|\bauditLog\s*\()"
)


def _iter_packed_lines(repo_content: str):
    """Yield (filename, lineno_in_file, text). Understands '### FILE: <path>' headers
    emitted by git_fetcher.pack_repo so findings cite real file:line coordinates."""
    cur_file = "(unknown)"
    lineno = 0
    for raw in repo_content.splitlines():
        m = re.match(r"#{2,3}\s*FILE:\s*(.+)$", raw.strip())
        if m:
            cur_file = m.group(1).strip()
            lineno = 0
            continue
        lineno += 1
        yield cur_file, lineno, raw


def compliance_scan(repo_content: str, repo_name: str = "unknown") -> str:
    findings = []
    scanned = list(_iter_packed_lines(repo_content))

    for code, label, patterns in OWASP_LLM_CHECKS:
        compiled = [re.compile(p) for p in patterns]
        hits = []
        for fname, lineno, text in scanned:
            if any(rx.search(text) for rx in compiled):
                hits.append(f"    {fname}:{lineno}: {text.strip()[:100]}")
                if len(hits) >= 5:
                    break
        status = "⚠️ REVIEW" if hits else "— no keyword match (manual review still required)"
        entry = f"{code} {label}: {status}"
        if hits:
            entry += "\n" + "\n".join(hits)
        findings.append(entry)

    has_logging = any(_LOGGING_RE.search(text) for _, _, text in scanned)
    eu_status = (
        "detected logging/audit API usage"
        if has_logging
        else "no logging/audit API detected — EU AI Act Art. 12 record-keeping may be absent"
    )
    findings.append(f"\nEU AI Act Article 12 (record-keeping) indicator: {eu_status}")

    header = (
        f"REPOMIND Security Heuristic Pre-Scan — {repo_name}\n"
        + "=" * 64 + "\n"
        + "HEURISTIC PRE-SCAN — flags lines for human review. This is NOT a certified\n"
        + "security control or a regulatory compliance attestation. A clear result does\n"
        + "not guarantee security. Covers 5 OWASP-LLM risk surfaces + an Art. 12 indicator.\n"
        + "=" * 64 + "\n"
    )
    return header + "\n".join(findings)
