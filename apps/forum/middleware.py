from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

from .services.presence import record_user_presence


class UserActivityMiddleware(MiddlewareMixin):
    """Фиксирует присутствие в Redis и редко синхронизирует ``last_activity`` в БД."""
    def process_request(self, request):

        if not request.user.is_authenticated:
            return
        record_user_presence(request.user.pk)
        throttle = int(getattr(settings, "FORUM_LAST_ACTIVITY_DB_SYNC_SECONDS", 300))
        key = f"forum:sync_last_act:{request.user.pk}"

        if cache.add(key, "1", timeout=throttle):
            request.user.update_last_activity()
