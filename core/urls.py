from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

import core.admin


urlpatterns = [
    # ----------------- CABINET -------------------
    path("cabinet/", admin.site.urls),
    path("cabinet/logs/", include("log_viewer.urls")),
    # --------------- OTHER URL"s -----------------
    path("accounts/", include("allauth.urls")),
    path("captcha/", include("captcha.urls")),
    path("robots.txt", include("apps.robots.urls")),
    path("sitemap.xml", include("apps.sitemap.urls")),
    path("summernote/", include("django_summernote.urls")),
    # -------------- PROJECT URL"s ----------------
    path("", include("apps.site_pages.urls")),
    path("", include("apps.forum.urls")),
]


# --------------------------- SWAGGER (API docs) ------------------------
try:
    from core.settings.components.api.swagger import swagger_urlpatterns

    urlpatterns += swagger_urlpatterns
except Exception:
    pass

# --------------------------- URLS EXTENDED ----------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
