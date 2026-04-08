"""
Язык админки берётся из куки django_admin_language (path=/cabinet/).
На запросы вне /cabinet/ эта кука не отправляется, поэтому язык сайта не меняется.
"""
from django.conf import settings
from django.utils import translation


def AdminLanguageMiddleware(get_response):

    def middleware(request):
        admin_path = getattr(settings, "LANGUAGE_ADMIN_COOKIE_PATH", "/cabinet/")
        cookie_name = getattr(settings, "LANGUAGE_ADMIN_COOKIE_NAME", "django_admin_language")
        admin_prefix = admin_path.rstrip("/")  # "/cabinet"

        if request.path.startswith(admin_prefix + "/") or request.path == admin_prefix:
            lang = request.COOKIES.get(cookie_name)

            if lang:
                allowed = [code for code, _ in getattr(settings, "LANGUAGES", [])]

                if lang in allowed:
                    translation.activate(lang)
                    request.LANGUAGE_CODE = lang
        return get_response(request)

    return middleware
