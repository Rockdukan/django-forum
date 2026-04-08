from django.utils.deprecation import MiddlewareMixin


class PermissionsPolicyMiddleware(MiddlewareMixin):
    """
    Устанавливает заголовок Permissions-Policy (бывший Feature-Policy),
    отключая неиспользуемые возможности браузера и снижая поверхность атаки.
    """
    def process_response(self, request, response):
        # Отключаем опасные или редко нужные фичи по умолчанию
        response["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        return response
