from django.contrib.sitemaps.views import sitemap
from django.urls import path

from .views import sitemaps

urlpatterns = [
    path("", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
]
