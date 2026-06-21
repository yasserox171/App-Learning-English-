"""Unified API error handling (master prompt §10)."""
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Wrap DRF errors in a consistent envelope.

    Shape:
        {"error": {"status": 400, "detail": ...}}
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        detail = detail["detail"]

    response.data = {
        "error": {
            "status": response.status_code,
            "detail": detail,
        }
    }
    return response
