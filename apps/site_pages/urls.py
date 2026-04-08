from django.urls import path

from . import views

app_name = "site_pages"

urlpatterns = [
    path("about/", views.about_page, name="about"),
    path("contacts/", views.contacts_page, name="contacts"),
    path("privacy/", views.privacy_page, name="privacy"),
    path("rules/", views.rules_page, name="rules"),
]
