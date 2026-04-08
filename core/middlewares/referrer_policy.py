from django.utils.deprecation import MiddlewareMixin


class ReferrerPolicyMiddleware(MiddlewareMixin):
    """
    Устанавливает заголовок Referrer-Policy для ограничения
    объёма данных, передаваемых в Referer (безопасность и приватность).
    """
    def process_response(self, request, response):
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
