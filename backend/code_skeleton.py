"""
AST-lite code-skeleton compressor — for the EXPLORATION / triage phase only.

Instead of sending whole file bodies to the model just to figure out *where* the answer
lives, we send a compact skeleton: imports + class/function signatures + the first
docstring line, with bodies collapsed to `...`. The full file is still on disk and is
fetched verbatim for the deep pass — so this is reversible (Headroom-CCR style) but
dependency-free (pure regex, runs on the MacBook, no tree-sitter / no GPU).

Honest scope (deep-research 2026-07, verified): general coding ≈ 15-20% token cut;
high-ratio subtasks (code search, codebase exploration, issue triage) 47-92%. We use it
ONLY to build cheaper exploration context — never for the deep pass that must see real code.
"""
import re

# Lines we KEEP verbatim in the skeleton (structure, not logic).
_KEEP = re.compile(
    r"""^\s*(
        import\s | from\s.+\simport | \#include\b | using\s | package\s | require\b | use\s |     # imports
        (async\s+)?def\s | class\s | (export\s+)?(async\s+)?function\s | func\s |                  # defs
        (public|private|protected|static|final|abstract)\s | interface\s | struct\s | enum\s |    # decls
        type\s | trait\s | impl\s | module\s | fn\s |                                              # more decls
        @\w+ | \#\[                                                                                # decorators/attrs
    )""",
    re.X,
)
# A signature line that opens a body (ends with { or : or ( continuation) → keep + mark body.
_OPENS_BODY = re.compile(r"[:{]\s*$|\)\s*[:{]?\s*$")
# Docstring / leading comment we keep (first line only).
_DOC = re.compile(r'^\s*(""".*?"""|\'\'\'.*?\'\'\'|//\s*\S|#\s*\S|/\*)', re.S)


def skeletonize(code: str) -> str:
    """Return a structure-only skeleton of `code` (bodies collapsed to `...`)."""
    out, dropped, prev_kept_sig = [], False, False
    for line in code.splitlines():
        keep = bool(_KEEP.match(line))
        # keep a single docstring/comment line right under a signature we just kept
        doc = prev_kept_sig and bool(_DOC.match(line.strip()[:3] and line))
        if keep or doc:
            if dropped:
                out.append(_indent(line) + "...")
                dropped = False
            out.append(line.rstrip())
            prev_kept_sig = keep and bool(_OPENS_BODY.search(line))
        else:
            dropped = True
            prev_kept_sig = False
    if dropped:
        out.append("...")
    return "\n".join(out)


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def compress_repo_context(packed: str) -> str:
    """Skeletonize a packed multi-file context. Preserves `# FILE:`/`# REPO:` headers."""
    blocks, cur = [], []
    for line in packed.splitlines():
        if line.startswith(("# FILE:", "# REPO:", "=== ", "--- ")):
            if cur:
                blocks.append("\n".join(cur))
                cur = []
            blocks.append(line)  # header stays verbatim
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return "\n".join(b if b.startswith(("# FILE:", "# REPO:", "=== ", "--- ")) else skeletonize(b) for b in blocks)
