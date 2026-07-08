import os
import re
import hashlib
import subprocess
from pathlib import Path

CACHE_DIR = Path("/tmp/repos")
CACHE_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 100_000   # bytes — skip huge files
MAX_TOTAL_TOKENS = 200_000  # token budget per repo
SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff",
                   ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".zip", ".tar",
                   ".gz", ".bin", ".pkl", ".pt", ".safetensors", ".onnx",
                   ".lock", ".sum"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv",
             "dist", "build", ".next", ".nuxt", "vendor"}


def _repo_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


def clone_or_pull(repo_url: str) -> Path:
    """Clone repo if not cached; return local path."""
    key = _repo_key(repo_url)
    dest = CACHE_DIR / key
    if dest.exists():
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only", "-q"],
                       capture_output=True, timeout=30)
    else:
        subprocess.run(["git", "clone", "--depth=1", "-q", repo_url, str(dest)],
                       check=True, timeout=120)
    return dest


def walk_repo_files(repo_path: Path):
    """Yield (relpath:str, content:str) for every eligible source file in the repo."""
    for fpath in sorted(repo_path.rglob("*")):
        if not fpath.is_file():
            continue
        parts = set(fpath.relative_to(repo_path).parts)
        if parts & SKIP_DIRS:
            continue
        if fpath.suffix.lower() in SKIP_EXTENSIONS:
            continue
        if fpath.stat().st_size > MAX_FILE_SIZE:
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        yield str(fpath.relative_to(repo_path)), content


def file_manifest(repo_path: Path):
    """Return [(relpath, approx_tokens, first_line)] — a compact index for triage."""
    manifest = []
    for rel, content in walk_repo_files(repo_path):
        first = next((l.strip() for l in content.splitlines() if l.strip()), "")
        manifest.append((rel, max(1, len(content) // 4), first[:80]))
    return manifest


def pack_selected(repo_path: Path, selected: list[str], token_budget: int = MAX_TOTAL_TOKENS) -> str:
    """Pack only the named files (used by Gemma triage to build a focused context)."""
    want = set(selected)
    lines, approx = [], 0
    for rel, content in walk_repo_files(repo_path):
        if rel not in want:
            continue
        chunk = f"\n\n### FILE: {rel}\n" + content
        ct = len(chunk) // 4
        if approx + ct > token_budget:
            lines.append(f"\n\n### [TRUNCATED — budget {token_budget} tokens reached]")
            break
        lines.append(chunk)
        approx += ct
    return "".join(lines)


def pack_repo(repo_path: Path, token_budget: int = MAX_TOTAL_TOKENS) -> str:
    """Walk repo, concatenate files into one string with '### FILE:' headers."""
    lines = []
    approx_tokens = 0
    skipped_large = []

    for fpath in sorted(repo_path.rglob("*")):
        if not fpath.is_file():
            continue
        parts = set(fpath.relative_to(repo_path).parts)
        if parts & SKIP_DIRS:
            continue
        if fpath.suffix.lower() in SKIP_EXTENSIONS:
            continue
        if fpath.stat().st_size > MAX_FILE_SIZE:
            skipped_large.append(str(fpath.relative_to(repo_path)))
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel = fpath.relative_to(repo_path)
        chunk = f"\n\n### FILE: {rel}\n" + content
        chunk_tokens = len(chunk) // 4

        if approx_tokens + chunk_tokens > token_budget:
            lines.append(f"\n\n### [TRUNCATED — budget {token_budget} tokens reached]")
            break
        lines.append(chunk)
        approx_tokens += chunk_tokens

    if skipped_large:
        note = (f"\n\n### [NOTE: {len(skipped_large)} file(s) >"
                f" {MAX_FILE_SIZE // 1000}KB omitted from context: "
                + ", ".join(skipped_large[:10])
                + (" …" if len(skipped_large) > 10 else "") + "]")
        lines.append(note)

    return "".join(lines)


def get_repo_name(url: str) -> str:
    m = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else url
