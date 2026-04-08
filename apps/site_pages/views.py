from django.shortcuts import render

from .models import AboutPage, ContactsPage, PrivacyPage, RulesPage


def render_solo_page(request, model_class, fallback_template: str):
    """
    Рендерит singleton (django-solo): при заполненных полях — общий шаблон, иначе legacy-заглушка.

    Args:
        request: HTTP-запрос.
        model_class: Подкласс BaseHtmlSingletonPage с get_solo().
        fallback_template: Шаблон по умолчанию до наполнения из админки.
    """
    obj = model_class.get_solo()

    if (obj.title or "").strip() or (obj.content or "").strip():
        return render(
            request,
            "site_pages/static_page.html",
            {"page": obj},
        )
    return render(request, fallback_template)


def about_page(request):
    """Страница «О нас»."""
    return render_solo_page(request, AboutPage, "site_pages/legacy/about.html")


def contacts_page(request):
    """Страница «Контакты»."""
    return render_solo_page(request, ContactsPage, "site_pages/legacy/contacts.html")


def privacy_page(request):
    """Страница «Конфиденциальность»."""
    return render_solo_page(request, PrivacyPage, "site_pages/legacy/privacy.html")


def rules_page(request):
    """Страница «Правила»."""
    return render_solo_page(request, RulesPage, "site_pages/legacy/rules.html")
