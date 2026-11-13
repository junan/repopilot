"""Guards the booking sample fixture layout used by later tool tests."""

from __future__ import annotations

from tests.support.sample_repo import BOOKING_SAMPLE_REPO


def test_booking_sample_repo_is_the_tool_test_fixture() -> None:
    assert BOOKING_SAMPLE_REPO.is_dir()
    assert (BOOKING_SAMPLE_REPO / "booking" / "handler.py").is_file()
    assert (BOOKING_SAMPLE_REPO / "booking" / "store.py").is_file()
    assert (BOOKING_SAMPLE_REPO / "tests" / "test_booking.py").is_file()
    assert (BOOKING_SAMPLE_REPO / "README.md").is_file()


def test_booking_sample_mentions_idempotency_bug() -> None:
    handler = (BOOKING_SAMPLE_REPO / "booking" / "handler.py").read_text()
    regression = (BOOKING_SAMPLE_REPO / "tests" / "test_booking.py").read_text()

    assert "idempotency_key" in handler
    assert "test_retry_with_same_idempotency_key_does_not_duplicate" in regression
