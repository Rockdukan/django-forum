import mimetypes

from captcha.fields import CaptchaField
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import Category, ContentReport, PollOption, Post, Topic
from .permissions import forum_captcha_exempt

User = get_user_model()


class RegisterForm(UserCreationForm):
    """Форма регистрации с email, паролями и капчей."""
    email = forms.EmailField(
        max_length=254,
        help_text=_("Введите действительный адрес электронной почты."))
    captcha = CaptchaField(label=_("Проверка"), help_text=_("Введите символы с картинки"))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Единый CSS-класс полей формы регистрации

        for name in ("username", "email", "password1", "password2"):
            self.fields[name].widget.attrs.setdefault("class", "auth-input")

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Пользователь с таким email уже существует."))
        return email


class HoneypotMixin(forms.Form):
    """
    Базовый Form: поле ``website`` попадает в ``declared_fields`` у наследников ModelForm.

    Notes:
        Пустое скрытое поле отсекает простых ботов; заполнение — ошибка валидации.
    """
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1", "class": "hp-field"}),
        label="")

    def clean_website(self):
        # Боты заполняют скрытое поле — у людей оно остаётся пустым

        if self.cleaned_data.get("website"):
            raise forms.ValidationError(_("Антиспам: поле должно быть пустым."))
        return ""


class CaptchaIfNewUserMixin:
    """
    Добавляет капчу для первых N не удалённых постов; персонал и модераторы без капчи.
    """
    def __init__(self, *args, user=None, **kwargs):
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        threshold = int(getattr(settings, "FORUM_CAPTCHA_MAX_POSTS", 3))

        need_captcha = (
            user
            and user.is_authenticated
            and not forum_captcha_exempt(user)
            and user.posts.filter(is_removed=False).count() < threshold
        )

        if need_captcha:
            self.fields["captcha"] = CaptchaField(
                label=_("Проверка"),
                help_text=_("Введите символы с картинки"))


class TopicForm(HoneypotMixin, CaptchaIfNewUserMixin, forms.ModelForm):
    """Создание темы: раздел, заголовок, тело, теги, антиспам."""
    forum = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label=_("Раздел"),
        required=True)
    tags = forms.CharField(
        required=False,
        label=_("Теги"),
        help_text=_("Через запятую, не больше 8 тегов"),
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": _("например: python, django")}))
    poll_question = forms.CharField(
        required=False,
        max_length=200,
        label=_("Вопрос опроса"),
        widget=forms.TextInput(attrs={"class": "form-input"}))
    poll_options = forms.CharField(
        required=False,
        label=_("Варианты опроса"),
        help_text=_("По одному варианту на строку; при заполненном вопросе нужно не меньше двух."),
        widget=forms.Textarea(attrs={"class": "form-textarea", "rows": 4}))

    class Meta:
        model = Topic
        fields = ["title", "content"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "content": forms.Textarea(attrs={"class": "form-textarea", "rows": 10}),
        }
        labels = {
            "title": _("Заголовок"),
            "content": _("Содержание"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        self.fields["forum"].widget.attrs.setdefault("class", "form-select")
        self.fields["forum"].queryset = Category.objects.all().order_by("order", "name")

    def clean(self):
        cleaned = super().clean()
        pq = (cleaned.get("poll_question") or "").strip()
        praw = (cleaned.get("poll_options") or "").strip()

        if pq or praw:

            if not pq:
                raise forms.ValidationError(_("Если заданы варианты, укажите вопрос опроса."))
            opts = [ln.strip() for ln in praw.splitlines() if ln.strip()]

            if len(opts) < 2:
                raise forms.ValidationError(_("Нужно минимум два непустых варианта ответа."))
            cleaned["poll_options_list"] = opts
        else:
            cleaned["poll_options_list"] = []
        return cleaned


class TopicEditForm(HoneypotMixin, forms.ModelForm):
    """Редактирование темы и текста первого сообщения."""
    edit_reason = forms.CharField(
        label=_("Причина правки"),
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={"class": "auth-input", "placeholder": _("Необязательно")}))
    tags = forms.CharField(
        required=False,
        label=_("Теги"),
        help_text=_("Через запятую, не больше 8 тегов"),
        widget=forms.TextInput(attrs={"class": "form-input"}))

    class Meta:
        model = Topic
        fields = ["title", "content"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-textarea", "rows": 10}),
        }
        labels = {
            "title": _("Заголовок"),
            "content": _("Текст первого сообщения"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["tags"].initial = ", ".join(
                self.instance.tags.order_by("name").values_list("name", flat=True)
            )


class PostForm(HoneypotMixin, CaptchaIfNewUserMixin, forms.ModelForm):
    """Ответ в теме (текст сообщения)."""
    class Meta:
        model = Post
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={"class": "reply-textarea", "rows": 10, "id": "reply-content"}),
        }
        labels = {
            "content": _("Сообщение"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)


class PostEditForm(HoneypotMixin, forms.ModelForm):
    """Редактирование текста существующего сообщения."""
    edit_reason = forms.CharField(
        label=_("Причина правки"),
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={"class": "auth-input", "placeholder": _("Необязательно")}))

    class Meta:
        model = Post
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "reply-textarea", "rows": 10}),
        }
        labels = {
            "content": _("Сообщение"),
        }


def attachment_allowed(content_type: str, name: str) -> bool:
    """
    Проверяет расширение и MIME вложения по настройкам форума.

    Args:
        content_type: Значение из upload (может быть пустым).
        name: Имя файла.

    Returns:
        True, если тип разрешён.
    """
    allowed = getattr(
        settings,
        "FORUM_ATTACHMENT_ALLOWED_EXTENSIONS",
        (".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".zip", ".txt"),
    )
    lower = name.lower()

    # Отсев по расширению без чтения содержимого

    if not any(lower.endswith(ext) for ext in allowed):
        return False
    ok_types = getattr(
        settings,
        "FORUM_ATTACHMENT_ALLOWED_MIME",
        (
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "application/pdf",
            "application/zip",
            "text/plain",
        ),
    )

    if content_type and content_type.split(";")[0].strip() in ok_types:
        return True
    guess = mimetypes.guess_type(name)[0]
    return guess in ok_types


def validate_attachment_list(files) -> list:
    """
    Валидирует список загрузок по числу, размеру и типу.

    Args:
        files: Итерируемый объект UploadedFile (или пусто).

    Returns:
        Список тех же файлов.

    Raises:
        ValidationError: При превышении лимитов или неразрешённом типе.
    """
    if not files:
        return []
    max_bytes = int(getattr(settings, "FORUM_ATTACH_MAX_BYTES", 5 * 1024 * 1024))
    max_n = int(getattr(settings, "FORUM_ATTACH_MAX_COUNT", 5))

    if len(files) > max_n:
        raise forms.ValidationError(_("Не больше %(n)s файлов.") % {"n": max_n})
    for upload in files:

        if upload.size > max_bytes:
            raise forms.ValidationError(_("Файл слишком большой."))
        ct = getattr(upload, "content_type", "") or ""

        if not attachment_allowed(ct, upload.name):
            raise forms.ValidationError(_("Тип файла не разрешён: %(name)s") % {"name": upload.name})
    return list(files)


class MoveTopicForm(forms.Form):
    """Выбор категории для переноса темы модератором."""
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by("order", "name"),
        label=_("Перенести в раздел"))


class HidePostForm(forms.Form):
    """Причина скрытия сообщения с публичной ленты."""
    reason = forms.CharField(
        max_length=500,
        label=_("Причина скрытия"),
        widget=forms.Textarea(attrs={"rows": 3, "class": "auth-input"}))


class SoftDeleteForm(forms.Form):
    """Необязательная причина мягкого удаления."""
    reason = forms.CharField(
        max_length=500,
        required=False,
        label=_("Причина (необязательно)"),
        widget=forms.Textarea(attrs={"rows": 2, "class": "auth-input"}))


class ContentReportForm(forms.ModelForm):
    """Текст жалобы на тему или сообщение."""
    class Meta:
        model = ContentReport
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(
                attrs={
                    "rows": 8,
                    "class": "form-textarea report-reason-input",
                    "placeholder": _("Опишите нарушение"),
                }),
        }
        labels = {"reason": _("Описание")}


class PrivateMessageComposeForm(forms.Form):
    """Новое личное сообщение по логину получателя."""
    to_username = forms.CharField(max_length=150, label=_("Получатель (логин)"))
    message = forms.CharField(
        label=_("Сообщение"),
        widget=forms.Textarea(attrs={"rows": 6, "class": "reply-textarea"}))


class PollVoteForm(forms.Form):
    """Выбор варианта в опросе темы."""
    option = forms.ModelChoiceField(queryset=PollOption.objects.none(), label=_("Ваш ответ"))

    def __init__(self, poll, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["option"].queryset = poll.options.all()


class IgnoredUsersManageForm(forms.ModelForm):
    """Правка списка игнорируемых пользователей."""
    class Meta:
        model = User
        fields = ["ignored_users"]
        labels = {"ignored_users": _("Не показывать темы и сообщения этих пользователей")}
        widgets = {
            "ignored_users": forms.SelectMultiple(
                attrs={
                    "class": "forum-select-multiple",
                    "size": "10",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ignored_users"].queryset = (
            User.objects.filter(is_active=True).exclude(pk=self.instance.pk).order_by("username")
        )
        self.fields["ignored_users"].required = False


class ForumUserEditForm(forms.ModelForm):
    """Редактирование email и полей форума в одной модели пользователя."""
    class Meta:
        model = User
        fields = [
            "email",
            "avatar",
            "signature",
            "notify_email_reply",
            "notify_email_mention",
            "notify_email_pm",
            "notify_email_moderation",
        ]
        widgets = {
            "signature": forms.Textarea(attrs={"rows": 4, "class": "auth-input"}),
        }
        labels = {
            "email": _("Email"),
            "avatar": _("Аватар"),
            "signature": _("Подпись"),
            "notify_email_reply": _("Письма о новых ответах в подписанных темах"),
            "notify_email_mention": _("Письма при @упоминании"),
            "notify_email_pm": _("Письма о личных сообщениях"),
            "notify_email_moderation": _("Письма о жалобах (для модераторов)"),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)

        if email and qs.exists():
            raise forms.ValidationError(_("Этот адрес уже занят."))
        return email
