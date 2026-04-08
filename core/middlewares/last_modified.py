import datetime

from django.http import HttpResponseNotModified
from django.utils.http import http_date, parse_http_date_safe
from django.utils.timezone import is_naive, make_aware


class LastModifiedMiddleware:
    """
    Middleware, устанавливающее заголовок Last-Modified в HTTP-ответе.

    Этот middleware проверяет несколько кандидатных атрибутов объекта
    страницы. Из найденных дат выбирается самая свежая (наибольшая).
    Если клиент отправляет заголовок If-Modified-Since и время
    последнего изменения объекта не новее, возвращается ответ с кодом
    304 Not Modified. В противном случае в ответ добавляется заголовок
    Last-Modified, установленный в формате HTTP.
    """
    # Атрибуты-источники даты изменения объекта
    CANDIDATE_ATTRS = [
        "last_modified",
        "last_published_at",
        "last_updated",
        "latest_revision_created_at",
        "created",
        "modified",
        "updated",
        "updated_at",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def get_last_modified(self, obj):
        """
        Возвращает самую свежую дату изменения из кандидатных
        атрибутов объекта.

        Проходит по списку CANDIDATE_ATTRS, и если значение найдено
        и является объектом datetime, то, если оно неосведомлённое
        (naive), преобразует его в осведомлённое (aware). После этого
        возвращает максимальное значение даты.

        Args:
            obj: Объект, из которого извлекается
                информация о дате изменения.

        Returns:
            datetime.datetime или None: Самая свежая дата изменения
                или None, если ни один атрибут не найден.
        """
        dates = []

        for attr in self.CANDIDATE_ATTRS:
            value = getattr(obj, attr, None)

            if isinstance(value, datetime.datetime):
                if is_naive(value):
                    value = make_aware(value)

                dates.append(value)

        if dates:
            return max(dates)

        return None

    def __call__(self, request):
        """
        Обрабатывает входящий HTTP-запрос и устанавливает
        Last-Modified в ответе.

        Если клиент отправляет заголовок If-Modified-Since,
        время которого больше или равно последней дате изменения
        объекта, возвращается ответ с кодом 304 Not Modified.

        Args:
            request (HttpRequest): Входящий HTTP-запрос.

        Returns:
            HttpResponse: Итоговый HTTP-ответ с добавленным
            заголовком Last-Modified (если применимо).
        """
        response = self.get_response(request)

        # Исключаем служебные пути и ошибки

        if response.status_code >= 400:
            return response
        elif request.path.startswith("/admin/"):
            return response
        elif request.path.startswith("/api/"):
            return response
        elif "Last-Modified" in response:
            return response

        # Пытаемся получить объект страницы из request
        # (либо из request.page, либо из context)
        obj = getattr(request, "page", None)

        if obj is None and hasattr(response, "context_data"):
            context = response.context_data

            if isinstance(context, dict):
                obj = context.get("page") or context.get("object")

        latest_date = self.get_last_modified(obj) if obj else None

        if latest_date:
            client_time = request.META.get("HTTP_IF_MODIFIED_SINCE")

            if client_time:
                client_dt = parse_http_date_safe(client_time)

                if client_dt and int(latest_date.timestamp()) <= client_dt:
                    return HttpResponseNotModified()

            lm_str = http_date(latest_date.timestamp())

            if "Last-Modified" not in response:
                response["Last-Modified"] = lm_str
        return response
