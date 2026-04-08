import time

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.utils.http import http_date
from django.views.decorators.cache import patch_cache_control


class CacheControlMiddleware:
    """Добавляет заголовки Cache-Control и Expires к ответам."""
    def __init__(self, get_response):
        """
        Инициализирует middleware и читает настройки кэширования.

        Args:
            get_response: Следующий обработчик в цепочке middleware.
        """
        self.get_response = get_response
        self.is_disabled = getattr(settings, "DISABLE_CACHE_CONTROL_MIDDLEWARE", False)

        # Если middleware отключён настройкой, исключаем его из цепочки.
        if self.is_disabled:
            raise MiddlewareNotUsed

        self.cache_max_age = getattr(settings, "CACHE_MAX_AGE", 3600)
        self.cache_shared_max_age = getattr(
            settings,
            "CACHE_SHARED_MAX_AGE",
            self.cache_max_age,
        )

    def __call__(self, request):
        """
        Обрабатывает запрос и добавляет cache-заголовки в ответ.

        Args:
            request: HTTP-запрос.

        Returns:
            HttpResponse: Ответ с заголовками кэширования.
        """
        response = self.get_response(request)

        # Добавляем параметры клиентского и proxy-кэширования.
        patch_cache_control(
            response,
            max_age=self.cache_max_age,
            s_maxage=self.cache_shared_max_age,
        )

        # Формируем абсолютное время истечения кэша.
        response["Expires"] = http_date(time.time() + self.cache_max_age)

        return response
