from django.http import HttpResponse
from django.views.decorators.cache import cache_page

from .models import RobotsTxt


@cache_page(60 * 60)
def robots_txt(request):
    """Возвращает содержимое robots.txt из БД."""
    # Пытаемся отдать текст из singleton-модели; при сбое — безопасный дефолт
    try:
        robots = RobotsTxt.get_solo()

        if robots and robots.content:
            return HttpResponse(robots.content, content_type="text/plain")
    except Exception:
        pass

    # Минимальный robots.txt, чтобы не блокировать индексацию при ошибке БД
    return HttpResponse("User-agent: *\nAllow: /", content_type="text/plain")
