from django.http import JsonResponse


class UserAgentValidationMiddleware:
    """Middleware для проверки User-Agent."""
    def __init__(self, get_response):
        self.get_response = get_response
        self.blocked_agents = ["curl", "wget", "python-requests", "scrapy", "bot"]

    def __call__(self, request):
        # Применяем только к API эндпоинтам

        if request.path.startswith("/api/"):
            user_agent = request.META.get("HTTP_USER_AGENT", "")

            # Блокируем пустые User-Agent

            if not user_agent:
                return JsonResponse({"detail": "User-Agent header required"}, status=403)

            # Блокируем известных ботов

            if any(bot in user_agent.lower() for bot in self.blocked_agents):
                return JsonResponse({"detail": "Access denied"}, status=403)

        response = self.get_response(request)
        return response
