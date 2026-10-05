"""Checks shared by later clustering routes."""

from backend.utils.errors import DatasetTooSmallError, InvalidKError, KTooLargeError

MIN_SAMPLES = 10
MIN_K = 2
MAX_K = 10


def validate_k(k: int, sample_count: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or k < MIN_K or k > MAX_K:
        raise InvalidKError()
    if sample_count < MIN_SAMPLES:
        raise DatasetTooSmallError()
    if k >= sample_count:
        raise KTooLargeError()
