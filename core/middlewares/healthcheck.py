from django.conf import settings
from django.http import JsonResponse


class HealthcheckMiddleware:
    """
    Отдает health-check ответы без захода в остальной стек приложения.

    Полезно для orchestrator/readiness probes.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.health_path = getattr(settings, "HEALTHCHECK_PATH", "/healthz")
        self.readiness_path = getattr(settings, "READINESS_PATH", "/readyz")

    def __call__(self, request):
        if request.path == self.health_path:
            return JsonResponse({"status": "ok"})

        if request.path == self.readiness_path:
            return JsonResponse({"status": "ready"})

        return self.get_response(request)
