from django.utils.deprecation import MiddlewareMixin


class ForceSameSiteNoneForLocalhost(MiddlewareMixin):
    """
    Django 2.x не умеет SameSite=None.
    Поэтому для запросов с localhost вручную дописываем:
      SameSite=None; Secure
    Только для sessionid и csrftoken.
    """
    LOCAL_ORIGINS = {
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    }

    def process_response(self, request, response):
        origin = request.META.get("HTTP_ORIGIN")

        if origin in self.LOCAL_ORIGINS:
            for key in ("sessionid", "csrftoken"):
                if key in response.cookies:
                    morsel = response.cookies[key]
                    # вручную добавляем атрибут
                    morsel["samesite"] = "None"
                    morsel["secure"] = True  # SameSite=None требует Secure

        return response
