import logging
import time

logger = logging.getLogger("timing")


class TimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration = time.monotonic() - start
        logger.info("%s %s %.3fs", request.method, request.path, duration)
        return response
