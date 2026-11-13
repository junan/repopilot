# Booking sample repository

Intentional demo fixture for RepoPilot. It models a small booking service that
creates **duplicate reservations** when clients retry with the same idempotency
key.

This tree is the only sample repository used by repository-tool tests.

## Layout

- `booking/handler.py` — reservation create path (bug: ignores idempotency keys)
- `booking/store.py` — in-memory reservation store
- `tests/test_booking.py` — regression that currently fails on duplicate retries

## Run the failing test

```bash
cd examples/booking-sample
python -m pytest tests/test_booking.py -q
```
