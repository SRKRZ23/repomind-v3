"""
Tamper-evident, append-only audit log for the SC-TIR trace.

Makes the EU AI Act Article 12 "record-keeping" claim real AND attestable: every analysis
and every agent step is persisted to a durable JSONL file with:
  - a monotonic sequence number that SURVIVES process restart (seeded from the file),
  - a SHA-256 hash chain (each record commits to the previous record's hash) so any
    deletion or edit of an earlier record is detectable — tamper-evident, not just append,
  - write failures surfaced to stderr (never silently dropped) while never breaking the
    request path.

Set AUDIT_LOG to a WORM / restricted-permission path in production (default ./data, mounted
as a persistent volume in docker-compose). Set AUDIT_SIGNING_KEY (hex) to a KMS/HSM-managed
key in production so signatures remain verifiable and attributable across restarts.
"""
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

# Ed25519 signing is optional: if `cryptography` is installed (it's in requirements.txt /
# the Docker image), each record's hash is also SIGNED with an Ed25519 key, so a third
# party can verify authenticity with the public key — not just detect tampering via the
# chain. Absent the lib, we degrade to hash-chain-only (still tamper-evident).
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    _CRYPTO = True
except Exception:
    _CRYPTO = False

# Default to a persistent (non-/tmp) path; mount a volume at ./data in production.
AUDIT_PATH = Path(os.getenv("AUDIT_LOG", "data/repomind_audit.jsonl"))
_GENESIS = "0" * 64


def _load_signing_key():
    """Load the Ed25519 private key from AUDIT_SIGNING_KEY (hex), else generate one and
    print the public key so operators can pin it. Returns (private_key_or_None, pub_hex)."""
    if not _CRYPTO:
        return None, None
    hexkey = os.getenv("AUDIT_SIGNING_KEY", "")
    try:
        priv = (Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hexkey))
                if hexkey else Ed25519PrivateKey.generate())
    except Exception:
        priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes_raw().hex()
    if not hexkey:
        print(f"[audit] generated ephemeral Ed25519 audit key; public={pub_hex}", file=sys.stderr)
    return priv, pub_hex


_SIGN_KEY, _PUB_HEX = _load_signing_key()


def _load_state():
    """Recover (seq, last_hash) from the existing log so restarts don't reset the chain."""
    seq, last = 0, _GENESIS
    try:
        if AUDIT_PATH.exists():
            with AUDIT_PATH.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        seq = rec.get("seq", seq)
                        last = rec.get("hash", last)
                    except Exception:
                        continue
    except Exception:
        pass
    return seq, last


_SEQ, _LAST_HASH = _load_state()


def new_session(repo_urls, question, mode) -> str:
    sid = uuid.uuid4().hex[:12]
    record(sid, "session_start", {"repo_urls": repo_urls, "question": question, "mode": mode})
    return sid


def record(session_id: str, step: str, payload) -> None:
    global _SEQ, _LAST_HASH
    _SEQ += 1
    entry = {
        "seq": _SEQ,
        "ts": time.time(),
        "session": session_id,
        "step": step,
        "payload": payload,
        "prev_hash": _LAST_HASH,
    }
    body = json.dumps(entry, default=str, sort_keys=True)
    entry["hash"] = hashlib.sha256((_LAST_HASH + body).encode("utf-8")).hexdigest()
    if _SIGN_KEY is not None:
        entry["sig"] = _SIGN_KEY.sign(entry["hash"].encode("utf-8")).hex()
        entry["pubkey"] = _PUB_HEX
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as f:  # append-only mode
            f.write(json.dumps(entry, default=str) + "\n")
        _LAST_HASH = entry["hash"]
    except Exception as e:
        # Never break the request path — but surface the failure (do not swallow silently).
        print(f"[audit] WRITE FAILED seq={_SEQ}: {e}", file=sys.stderr)


_META = ("hash", "sig", "pubkey")  # fields added AFTER the hash is computed


def verify_chain(path: Path = None) -> tuple[bool, int]:
    """Re-derive the hash chain to detect tampering. Returns (ok, records_checked)."""
    path = path or AUDIT_PATH
    prev = _GENESIS
    n = 0
    if not path.exists():
        return True, 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            stored = rec.get("hash")
            body = json.dumps({k: rec[k] for k in rec if k not in _META},
                              default=str, sort_keys=True)
            expect = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()
            if rec.get("prev_hash") != prev or stored != expect:
                return False, n
            prev = stored
            n += 1
    return True, n


def verify_signatures(path: Path = None, expected_pubkey: str = None) -> tuple[bool, int]:
    """Verify each record's Ed25519 signature. Returns (ok, signed_records_checked).

    Pass expected_pubkey (the operator's pinned public key, hex) for ANTI-FORGERY: every
    record's key must match it, so a full re-sign with an attacker's key is rejected.
    Without it, this proves signature/hash consistency (tamper-evidence) but not authenticity
    against a wholesale re-sign — pin the key out-of-band for evidentiary use.
    No-op (True, 0) if crypto/sigs absent."""
    path = path or AUDIT_PATH
    if not _CRYPTO or not path.exists():
        return True, 0
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "sig" not in rec or "pubkey" not in rec:
                continue
            if expected_pubkey is not None and rec["pubkey"] != expected_pubkey:
                return False, n  # key pinning: reject records not signed by the pinned key
            try:
                pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(rec["pubkey"]))
                pub.verify(bytes.fromhex(rec["sig"]), rec["hash"].encode("utf-8"))
                n += 1
            except Exception:
                return False, n
    return True, n
