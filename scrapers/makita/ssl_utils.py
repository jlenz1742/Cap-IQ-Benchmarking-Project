"""Workaround for makitatools.com's incomplete TLS certificate chain.

The server serves a leaf cert for ``*.makitatools.com`` signed by "Go Daddy
Secure Certificate Authority - G2" but does not send that intermediate
certificate in the handshake. Browsers paper over this (they cache
intermediates seen elsewhere, or fetch missing ones via AIA), but strict
verifiers like Python's ``ssl`` module do not, and fail with
"unable to get local issuer certificate".

The fix isn't to skip verification — it's to supply the (public, standard)
missing intermediate ourselves alongside the normal trust store.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import certifi

_CERT_DIR = Path(__file__).parent / "certs"
GODADDY_G2_INTERMEDIATE = _CERT_DIR / "godaddy_g2_intermediate.pem"

_cached_bundle_path: str | None = None


def ca_bundle_with_godaddy_intermediate() -> str:
    """Path to a CA bundle combining certifi's roots with the missing
    GoDaddy G2 intermediate, generated once per process and reused."""
    global _cached_bundle_path
    if _cached_bundle_path is not None and Path(_cached_bundle_path).exists():
        return _cached_bundle_path

    combined = Path(certifi.where()).read_text() + "\n" + GODADDY_G2_INTERMEDIATE.read_text()
    fd, path = tempfile.mkstemp(prefix="makita_us_ca_bundle_", suffix=".pem")
    with open(fd, "w") as f:
        f.write(combined)

    _cached_bundle_path = path
    return path
