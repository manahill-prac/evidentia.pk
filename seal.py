
"""
seal.py — CourtReady AI
========================
ROLE     : Crypto Engineer
ENGINEER : [Your Name]
PURPOSE  : Evidence sealing, hash generation, Supabase storage, and tamper verification.

KEY DESIGN DECISIONS:
  - Camera capture metadata (capture_timestamp) is recorded CLIENT-SIDE at moment of capture
    and passed in separately from file bytes. This prevents backdating — you cannot upload
    an old photo and claim it was captured "just now" because the seal records BOTH the
    capture time (from device) and the seal time (server UTC). Any gap > 5 minutes is flagged.
  - SHA-256 is applied to RAW bytes before any processing. The hash is the ground truth.
  - Evidence ID is deterministic: first 8 chars of hash + 8-char random suffix = globally unique.
  - All timestamps stored as ISO 8601 UTC strings for legal unambiguity.
"""

import hashlib
import hmac
import os
import secrets
import datetime
from typing import Optional
from supabase import create_client, Client


# =============================
# SUPABASE CLIENT
# =============================

def _get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment variables."
        )
    return create_client(url, key)


# =============================
# INTERNAL HELPERS
# =============================

def _generate_hash(file_bytes: bytes) -> str:
    """SHA-256 hash of raw file bytes. This is the evidence fingerprint."""
    return hashlib.sha256(file_bytes).hexdigest()


def _generate_evidence_id(hash_value: str) -> str:
    """
    Evidence ID format: CR-{first 8 chars of hash in uppercase}-{8 random hex chars}
    Example: CR-A3F92C11-7D4E8B2A
    - Prefix 'CR' = CourtReady
    - Hash fragment: ties ID to specific evidence mathematically
    - Random suffix: prevents enumeration/guessing of other evidence IDs
    """
    hash_prefix = hash_value[:8].upper()
    random_suffix = secrets.token_hex(4).upper()
    return f"CR-{hash_prefix}-{random_suffix}"


def _get_utc_now() -> str:
    """Server-side UTC timestamp in ISO 8601 format."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _check_capture_seal_gap(
    capture_timestamp: Optional[str],
    seal_timestamp: str
) -> dict:
    """
    Validates the time gap between when media was captured vs when it was sealed.
    A large gap (> 5 minutes) raises a CAUTION flag but does NOT block sealing.
    This is metadata for lawyers — not a hard rejection.

    Returns:
        {
            "gap_seconds": int or None,
            "flag": "OK" | "CAUTION" | "UNKNOWN",
            "message": str
        }
    """
    if not capture_timestamp:
        return {
            "gap_seconds": None,
            "flag": "UNKNOWN",
            "message": "No capture timestamp provided. Gap cannot be verified."
        }

    try:
        # Parse both timestamps
        fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
        capture_dt = datetime.datetime.strptime(capture_timestamp, fmt)
        seal_dt = datetime.datetime.strptime(seal_timestamp, fmt)
        gap = (seal_dt - capture_dt).total_seconds()

        if gap < 0:
            return {
                "gap_seconds": int(gap),
                "flag": "CAUTION",
                "message": f"Capture timestamp is AFTER seal timestamp by {abs(int(gap))}s. Clock mismatch or backdating suspected."
            }
        elif gap <= 300:   # 5 minutes
            return {
                "gap_seconds": int(gap),
                "flag": "OK",
                "message": f"Evidence sealed within {int(gap)} seconds of capture. Strong authenticity signal."
            }
        else:
            minutes = int(gap // 60)
            return {
                "gap_seconds": int(gap),
                "flag": "CAUTION",
                "message": f"Evidence sealed {minutes} minutes after capture. Consider noting this in legal documentation."
            }
    except (ValueError, TypeError):
        return {
            "gap_seconds": None,
            "flag": "UNKNOWN",
            "message": "Could not parse capture timestamp format."
        }


# =============================
# PUBLIC API
# =============================

def seal_evidence(
    file_bytes: bytes,
    file_name: str = "evidence",
    file_type: str = "image",
    capture_timestamp: Optional[str] = None,
    location_metadata: Optional[dict] = None,
    submitted_by: Optional[str] = "anonymous"
) -> dict:
    """
    Seals evidence by generating a cryptographic hash and storing in Supabase.

    Args:
        file_bytes       : Raw bytes of the uploaded/captured file
        file_name        : Original filename (for records)
        file_type        : "image" | "video" | "audio" | "document"
        capture_timestamp: ISO 8601 UTC string of when media was captured
                           (passed from device camera at moment of capture)
        location_metadata: Optional dict with GPS data e.g. {"lat": 31.5, "lon": 74.3}
        submitted_by     : Identifier for the submitting user (anonymized by default)

    Returns:
        {
            "evidence_id"        : str,   # Unique ID for this evidence record
            "hash"               : str,   # SHA-256 of original file bytes
            "seal_timestamp"     : str,   # Server-side UTC time of sealing
            "capture_timestamp"  : str,   # Device-reported capture time (if provided)
            "capture_seal_gap"   : dict,  # Time gap analysis between capture and seal
            "file_name"          : str,
            "file_type"          : str,
            "file_size_bytes"    : int,
            "location_metadata"  : dict,
            "submitted_by"       : str,
            "status"             : "SEALED"
        }
    """
    # 1. Generate core cryptographic values
    hash_value      = _generate_hash(file_bytes)
    evidence_id     = _generate_evidence_id(hash_value)
    seal_timestamp  = _get_utc_now()

    # 2. Analyze capture-to-seal time gap
    gap_analysis = _check_capture_seal_gap(capture_timestamp, seal_timestamp)

    # 3. Build the evidence record
    record = {
        "evidence_id"       : evidence_id,
        "hash"              : hash_value,
        "seal_timestamp"    : seal_timestamp,
        "capture_timestamp" : capture_timestamp or "Not provided",
        "capture_seal_gap"  : gap_analysis,
        "file_name"         : file_name,
        "file_type"         : file_type,
        "file_size_bytes"   : len(file_bytes),
        "location_metadata" : location_metadata or {},
        "submitted_by"      : submitted_by,
        "status"            : "SEALED"
    }

    # 4. Write to Supabase
    try:
        supabase = _get_supabase()
        supabase.table("evidence_records").insert({
            "evidence_id"       : evidence_id,
            "hash"              : hash_value,
            "seal_timestamp"    : seal_timestamp,
            "capture_timestamp" : capture_timestamp or "",
            "gap_flag"          : gap_analysis["flag"],
            "gap_seconds"       : gap_analysis.get("gap_seconds"),
            "file_name"         : file_name,
            "file_type"         : file_type,
            "file_size_bytes"   : len(file_bytes),
            "location_lat"      : (location_metadata or {}).get("lat"),
            "location_lon"      : (location_metadata or {}).get("lon"),
            "submitted_by"      : submitted_by,
            "status"            : "SEALED"
        }).execute()
    except Exception as e:
        # Do NOT fail silently — surface the error
        record["supabase_error"] = str(e)
        record["status"] = "SEALED_LOCAL_ONLY"

    return record


def verify_hash(evidence_id: str, file_bytes: bytes) -> dict:
    """
    Verifies whether a file matches its original sealed hash in Supabase.

    Args:
        evidence_id : The Evidence ID issued at sealing (e.g. "CR-A3F92C11-7D4E8B2A")
        file_bytes  : Raw bytes of the file being verified

    Returns:
        {
            "verdict"          : "VERIFIED_ORIGINAL" | "TAMPERED" | "NOT_FOUND" | "ERROR",
            "evidence_id"      : str,
            "stored_hash"      : str or None,
            "submitted_hash"   : str,
            "seal_timestamp"   : str or None,
            "capture_timestamp": str or None,
            "gap_flag"         : str or None,
            "file_size_bytes"  : int or None,
            "verified_at"      : str,
            "message"          : str
        }
    """
    submitted_hash = _generate_hash(file_bytes)
    verified_at    = _get_utc_now()

    base_result = {
        "evidence_id"    : evidence_id,
        "submitted_hash" : submitted_hash,
        "verified_at"    : verified_at,
    }

    try:
        supabase = _get_supabase()
        response = supabase.table("evidence_records") \
            .select("*") \
            .eq("evidence_id", evidence_id) \
            .execute()

        if not response.data:
            return {
                **base_result,
                "verdict"          : "NOT_FOUND",
                "stored_hash"      : None,
                "seal_timestamp"   : None,
                "capture_timestamp": None,
                "gap_flag"         : None,
                "file_size_bytes"  : None,
                "message"          : f"No record found for Evidence ID: {evidence_id}. "
                                     f"Either the ID is incorrect or this evidence was not sealed with CourtReady AI."
            }

        record = response.data[0]
        stored_hash = record.get("hash", "")

        # Constant-time comparison prevents timing attacks
        hashes_match = hmac.compare_digest(stored_hash, submitted_hash)

        if hashes_match:
            verdict = "VERIFIED_ORIGINAL"
            message = (
                f"✓ This file is VERIFIED as the original sealed evidence. "
                f"The SHA-256 hash matches the record sealed on {record.get('seal_timestamp', 'unknown date')}. "
                f"This file has not been altered since sealing."
            )
        else:
            verdict = "TAMPERED"
            message = (
                f"✗ TAMPER DETECTED. The SHA-256 hash of this file does NOT match "
                f"the original sealed record. This file has been modified since it was "
                f"sealed on {record.get('seal_timestamp', 'unknown date')}. "
                f"This evidence should be treated as compromised."
            )

        return {
            **base_result,
            "verdict"          : verdict,
            "stored_hash"      : stored_hash,
            "seal_timestamp"   : record.get("seal_timestamp"),
            "capture_timestamp": record.get("capture_timestamp"),
            "gap_flag"         : record.get("gap_flag"),
            "file_size_bytes"  : record.get("file_size_bytes"),
            "message"          : message
        }

    except Exception as e:
        return {
            **base_result,
            "verdict"          : "ERROR",
            "stored_hash"      : None,
            "seal_timestamp"   : None,
            "capture_timestamp": None,
            "gap_flag"         : None,
            "file_size_bytes"  : None,
            "message"          : f"Verification failed due to a system error: {str(e)}"
        }


def get_evidence_record(evidence_id: str) -> Optional[dict]:
    """
    Retrieves the full sealed record from Supabase by Evidence ID.
    Used by pdf_generator.py to pull metadata for the legal PDF.

    Returns: Full record dict, or None if not found.
    """
    try:
        supabase = _get_supabase()
        response = supabase.table("evidence_records") \
            .select("*") \
            .eq("evidence_id", evidence_id) \
            .execute()
        return response.data[0] if response.data else None
    except Exception:
        return None


# =============================
# SUPABASE TABLE SCHEMA (SQL)
# =============================
# Run this once in Supabase SQL Editor to create the table:
#
# CREATE TABLE evidence_records (
#     id                BIGSERIAL PRIMARY KEY,
#     evidence_id       TEXT UNIQUE NOT NULL,
#     hash              TEXT NOT NULL,
#     seal_timestamp    TEXT NOT NULL,
#     capture_timestamp TEXT,
#     gap_flag          TEXT,
#     gap_seconds       INTEGER,
#     file_name         TEXT,
#     file_type         TEXT,
#     file_size_bytes   INTEGER,
#     location_lat      FLOAT,
#     location_lon      FLOAT,
#     submitted_by      TEXT,
#     status            TEXT,
#     created_at        TIMESTAMPTZ DEFAULT NOW()
# );
#
# CREATE INDEX idx_evidence_id ON evidence_records(evidence_id);
