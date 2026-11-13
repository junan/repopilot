"""Path to the only sample repository used by repository-tool tests."""

from __future__ import annotations

from pathlib import Path

# backend/tests/support -> repository root
REPO_ROOT = Path(__file__).resolve().parents[3]
BOOKING_SAMPLE_REPO = REPO_ROOT / "examples" / "booking-sample"
