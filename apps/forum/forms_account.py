"""Формы django-allauth (расширения под проект)."""
from allauth.account import app_settings
from allauth.account.adapter import get_adapter
from allauth.account.forms import default_token_generator
from allauth.account.internal.flows import password_reset
from allauth.account.utils import filter_users_by_email, user_email
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


class LoginOrEmailResetPasswordForm(forms.Form):
    """Сброс пароля: ввод email или логина; письмо уходит на email учётной записи."""
    login_or_email = forms.CharField(
        label=_("Логин или email"),
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "placeholder": _("Имя пользователя или email")}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.users = []

    def clean_login_or_email(self) -> str:
        raw = (self.cleaned_data.get("login_or_email") or "").strip()
        if not raw:
            raise forms.ValidationError(_("Обязательное поле."))

        User = get_user_model()
        adapter = get_adapter()
        users: list = []

        if "@" in raw:
            email = adapter.clean_email(raw.lower())
            users = filter_users_by_email(email, is_active=True, prefer_verified=True)
        else:
            u = User.objects.filter(username__iexact=raw, is_active=True).first()
            if u:
                users = [u]

        if not users and not app_settings.PREVENT_ENUMERATION:
            raise adapter.validation_error("unknown_email")

        self.users = users
        return raw

    def save(self, request, **kwargs) -> str:
        raw = (self.cleaned_data.get("login_or_email") or "").strip()
        token_generator = kwargs.get("token_generator", default_token_generator)

        if self.users:
            email_to = user_email(self.users[0]) or self.users[0].email or raw
        else:
            email_to = raw if "@" in raw else ""

        password_reset.request_password_reset(request, email_to, self.users, token_generator)
        return email_to
