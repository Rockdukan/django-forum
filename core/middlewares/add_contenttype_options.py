from django.utils.deprecation import MiddlewareMixin


class AddContentTypeOptionsMiddleware(MiddlewareMixin):
    """
    Middleware для установки заголовка X-Content-Type-Options: nosniff,
    который предотвращает нежелательное определение типа содержимого браузером.
    """
    def process_response(self, request, response):
        response["X-Content-Type-Options"] = "nosniff"
        return response
