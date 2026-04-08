import json
import logging
import time

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class RequestLogMiddleware(MiddlewareMixin):
    """Логирует входящие HTTP-запросы и ответы."""
    def __init__(self, get_response=None):
        """Инициализирует middleware и читает настройки логирования."""
        super().__init__(get_response)

        self.logger = logging.getLogger("request_logger")
        self.log_body = getattr(settings, "REQUEST_LOG_BODY", False)
        self.log_headers = getattr(settings, "REQUEST_LOG_HEADERS", False)
        self.log_response = getattr(settings, "REQUEST_LOG_RESPONSE", False)
        self.max_body_size = getattr(settings, "REQUEST_LOG_MAX_BODY_SIZE", 10 * 1024)
        self.masked_keys = {
            "access_token",
            "api_key",
            "authorization",
            "cookie",
            "password",
            "refresh_token",
            "secret",
            "set-cookie",
            "token",
        }
        self.exclude_paths = getattr(
            settings,
            "REQUEST_LOG_EXCLUDE_PATHS",
            ["/admin/jsi18n/", "/static/", "/media/"],
        )

    def process_request(self, request):
        """Фиксирует старт обработки запроса."""
        request.start_time = time.monotonic()

    def should_log(self, request, response=None):
        """Определяет, нужно ли логировать запрос/ответ."""
        path = request.path_info

        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False

        if response and response.get("Content-Type", "").startswith(
            ("image/", "video/", "audio/", "application/octet-stream")
        ):
            return False

        if (
            request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
            and "djdt" in request.META.get("HTTP_REFERER", "")
        ):
            return False

        return True

    def mask_dict(self, data):
        """Маскирует чувствительные поля в словаре."""
        masked = {}

        for key, value in data.items():
            key_lower = str(key).lower()
            if key_lower in self.masked_keys:
                masked[key] = "***"
            else:
                masked[key] = value

        return masked

    def process_response(self, request, response):
        """Логирует ответ после завершения обработки запроса."""
        if not self.should_log(request, response):
            return response

        duration = 0
        if hasattr(request, "start_time"):
            duration = round((time.monotonic() - request.start_time) * 1000)

        log_data = {
            "duration_ms": duration,
            "ip": self.get_client_ip(request),
            "method": request.method,
            "path": request.path,
            "request_id": getattr(request, "request_id", None),
            "status_code": response.status_code,
            "user": (
                request.user.username
                if getattr(request, "user", None) and request.user.is_authenticated
                else "anon"
            ),
        }

        if self.log_body and request.method in ("POST", "PUT", "PATCH"):
            try:
                if request.content_type == "application/json":
                    body = json.loads(request.body)
                    if isinstance(body, dict):
                        body = self.mask_dict(body)
                    log_data["body"] = body
                else:
                    log_data["body"] = self.mask_dict(dict(request.POST))
            except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError):
                log_data["body"] = "Error parsing body"

        if self.log_headers:
            log_data["headers"] = self.mask_dict(dict(request.headers))

        if self.log_response and response.get("Content-Type", "").startswith("application/json"):
            try:
                if hasattr(response, "content") and len(response.content) < self.max_body_size:
                    response_json = json.loads(response.content)
                    if isinstance(response_json, dict):
                        response_json = self.mask_dict(response_json)
                    log_data["response"] = response_json
            except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError):
                log_data["response"] = "Error parsing response"

        message = json.dumps(log_data, ensure_ascii=False, default=str)

        if response.status_code >= 500:
            self.logger.error("Request: %s", message)
        elif response.status_code >= 400:
            self.logger.warning("Request: %s", message)
        else:
            self.logger.info("Request: %s", message)

        return response

    def get_client_ip(self, request):
        """Возвращает IP клиента с учётом прокси."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "")
