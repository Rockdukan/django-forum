from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from django_ratelimit.decorators import ratelimit

from .dm_utils import (
    get_dm_inbox_summaries,
    get_or_create_dm_thread,
    mark_pm_notifications_read_for_thread,
    users_block_dm,
)
from .forms import (
    ContentReportForm,
    ForumUserEditForm,
    HidePostForm,
    IgnoredUsersManageForm,
    MoveTopicForm,
    PollVoteForm,
    PostEditForm,
    PostForm,
    PrivateMessageComposeForm,
    RegisterForm,
    SoftDeleteForm,
    TopicEditForm,
    TopicForm,
    validate_attachment_list,
)
from .ignore_utils import filter_posts_for_viewer, filter_topics_for_viewer, ignored_user_ids
from .models import (
    Category,
    ContentReport,
    Notification,
    Poll,
    PollOption,
    PollVote,
    Post,
    PostAttachment,
    PostRevision,
    PrivateMessage,
    PrivateThreadParticipant,
    Tag,
    Topic,
    TopicBookmark,
    TopicRevision,
    TopicSubscription,
)
from .permissions import (
    can_create_new_topic,
    can_delete_post,
    can_delete_topic,
    can_edit_post,
    can_edit_topic,
    can_moderate,
    can_reply_to_topic,
    posting_block_reason,
)
from .search import forum_search
from .services import (
    allow_user_post,
    is_duplicate_recent_post,
    notify_mentions,
    notify_topic_subscribers_new_post,
    record_user_post,
)
from .services.email_notify import try_email_pm
from .services.report_notify import notify_moderators_new_report
from .utils import sync_topic_tags_from_string

User = get_user_model()


def save_post_attachments(post, files):
    """Сохраняет валидированные вложения для поста."""
    if not files:
        return
    # Повторная валидация и создание записей вложений
    for f in validate_attachment_list(files):
        PostAttachment.objects.create(post=post, file=f, original_name=f.name)


def topic_legacy_redirect(request, category_slug, topic_id):
    # Старые URL с числовым id темы → 301 на канонический slug
    topic = Topic.all_objects.filter(pk=topic_id, category__slug=category_slug).first()

    if not topic:
        raise Http404(_("Тема не найдена."))
    return redirect(topic.get_absolute_url(), permanent=True)


def index(request):
    # Главная: категории, топ по просмотрам/ответам, последние темы
    categories = Category.objects.filter(parent__isnull=True).order_by("order", "name").prefetch_related("children")
    popular_topics = list(
        filter_topics_for_viewer(
            Topic.objects.select_related("author", "category")
            .annotate(post_count=Count("posts"))
            .order_by("-views", "-post_count", "-created_at"),
            request.user,
        )[:5],
    )
    recent_topics = list(
        filter_topics_for_viewer(
            Topic.objects.select_related("author", "category").order_by("-created_at"),
            request.user,
        )[:5],
    )

    popular_tags = (
        Tag.objects.annotate(topic_count=Count("topics"))
        .filter(topic_count__gt=0)
        .order_by("-topic_count", "name")[:40]
    )

    context = {
        "categories": categories,
        "popular_topics": popular_topics,
        "recent_topics": recent_topics,
        "popular_tags": popular_tags,
    }
    return render(request, "forum/index.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    subcategories = category.children.all().order_by("order", "name")
    filter_param = request.GET.get("filter", "all")
    topic_base = Topic.objects.filter(category_id__in=category.subtree_ids()).select_related("category", "author")
    topic_base = filter_topics_for_viewer(topic_base, request.user)

    # Пресеты списка тем: новые за неделю, популярные, без ответов, все
    if filter_param == "new":
        topics = topic_base.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7))
    elif filter_param == "popular":
        topics = topic_base.annotate(reply_count=Count("posts")).order_by("-reply_count")
    elif filter_param == "unanswered":
        topics = topic_base.annotate(reply_count=Count("posts")).filter(reply_count=1)
    else:
        topics = topic_base

    paginator = Paginator(topics, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "forum/theme_list.html",
        {
            "category": category,
            "subcategories": subcategories,
            "page_obj": page_obj,
            "filter": filter_param,
        },
    )


def build_topic_detail_context(
    request,
    category,
    topic,
    *,
    count_views=True,
    reply_form=None,
    page_number=None,
    reply_submit_failed=False,
):
    """
    Собирает контекст для шаблона страницы темы (листинг постов и форма ответа).

    Args:
        request: Текущий запрос.
        category: Категория темы.
        topic: Объект темы.
        count_views: Увеличивать счётчик просмотров при рендере.
        reply_form: Уже заполненная форма ответа (после ошибки).
        page_number: Номер страницы пагинации постов.
        reply_submit_failed: Флаг для подсветки ошибки в шаблоне.

    Returns:
        Словарь контекста для ``theme_detail.html``.
    """
    if count_views:
        topic.increment_views()

    posts_qs = (
        topic.posts.filter(is_removed=False)
        .select_related("author")
        .prefetch_related("liked_by", "attachments")
    )

    if not can_moderate(request.user):
        posts_qs = posts_qs.filter(is_hidden=False)
        posts_qs = filter_posts_for_viewer(posts_qs, request.user)

    paginator = Paginator(posts_qs, 10)
    if page_number is None:
        page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    if reply_form is not None:
        form = reply_form
    elif request.user.is_authenticated:
        form = PostForm(user=request.user)
    else:
        form = None

    subscribed = False
    bookmarked = False

    if request.user.is_authenticated:
        subscribed = TopicSubscription.objects.filter(user=request.user, topic=topic).exists()
        bookmarked = TopicBookmark.objects.filter(user=request.user, topic=topic).exists()

    meta_description = (topic.content[:300] + "…") if len(topic.content) > 300 else topic.content
    poll = getattr(topic, "poll", None)
    poll_vote = None
    poll_vote_form = None
    poll_results = None

    if poll:
        poll_results = list(poll.options.annotate(vote_count=Count("votes")).order_by("order", "id"))

        if request.user.is_authenticated:
            poll_vote = PollVote.objects.filter(poll=poll, user=request.user).first()

            if poll_vote is None and not topic.is_closed:
                poll_vote_form = PollVoteForm(poll)
    return {
        "category": category,
        "topic": topic,
        "page_obj": page_obj,
        "form": form,
        "subscribed": subscribed,
        "bookmarked": bookmarked,
        "can_moderate": can_moderate(request.user),
        "can_edit_topic": can_edit_topic(request.user, topic),
        "can_reply": can_reply_to_topic(request.user, topic),
        "meta_description": meta_description,
        "og_title": topic.title,
        "reply_submit_failed": reply_submit_failed,
        "poll": poll,
        "poll_vote": poll_vote,
        "poll_vote_form": poll_vote_form,
        "poll_results": poll_results,
    }


def topic_detail(request, category_slug, topic_slug):
    category = get_object_or_404(Category, slug=category_slug)
    topic = Topic.get_for_view(request.user, category_slug, topic_slug)

    # Неверный slug категории или тема скрыта от текущего пользователя
    if not topic or topic.category_id != category.id:
        return render(
            request,
            "forum/topic_gone.html",
            {"category": category},
            status=404,
        )

    return render(
        request,
        "forum/theme_detail.html",
        build_topic_detail_context(request, category, topic),
    )


@login_required
def create_topic(request, category_slug):
    # Жёсткие ограничения: бан, режим «только чтение», гость
    if not can_create_new_topic(request.user):
        messages.error(request, str(posting_block_reason(request.user) or _("Нельзя создавать темы.")))
        return redirect("forum:index")
    category = get_object_or_404(Category, slug=category_slug)
    categories = Category.objects.all().order_by("order", "name")

    if request.method == "POST":
        form = TopicForm(request.POST, user=request.user)

        if form.is_valid():
            # Антиспам по кэшу и дубликатам текста
            allowed, err = allow_user_post(request.user)

            if not allowed:
                messages.error(request, err)
            elif is_duplicate_recent_post(request.user, None, form.cleaned_data["content"]):
                messages.error(request, _("Такое сообщение уже недавно отправлялось."))
            else:
                # Тема + первый пост + подписка автора на собственную тему
                selected_category = form.cleaned_data["forum"]
                topic = form.save(commit=False)
                topic.category = selected_category
                topic.author = request.user
                topic.save()
                sync_topic_tags_from_string(topic, form.cleaned_data.get("tags", ""))
                post = Post.objects.create(
                    topic=topic,
                    author=request.user,
                    content=form.cleaned_data["content"],
                )
                TopicSubscription.objects.get_or_create(user=request.user, topic=topic)
                record_user_post(request.user)
                # Разбор @ников в первом сообщении темы
                notify_mentions(
                    body=post.content,
                    actor=request.user,
                    topic=topic,
                    post=post,
                )
                pq = (form.cleaned_data.get("poll_question") or "").strip()
                opts = form.cleaned_data.get("poll_options_list") or []

                if pq and opts:
                    poll = Poll.objects.create(topic=topic, question=pq)

                    for i, text in enumerate(opts):
                        PollOption.objects.create(poll=poll, text=text[:200], order=i)
                return redirect(
                    "forum:topic_detail",
                    category_slug=selected_category.slug,
                    topic_slug=topic.slug,
                )
    else:
        form = TopicForm(user=request.user, initial={"forum": category})

    return render(
        request,
        "forum/theme_create.html",
        {"form": form, "category": category, "categories": categories},
    )


@login_required
def create_post(request, category_slug, topic_slug):
    category = get_object_or_404(Category, slug=category_slug)
    topic = Topic.get_for_view(request.user, category_slug, topic_slug)

    # Доступ к теме и право ответить проверяются до приёма POST
    if not topic or topic.category_id != category.id:
        return HttpResponseForbidden(_("Тема недоступна."))

    if not can_reply_to_topic(request.user, topic):
        return HttpResponseForbidden(_("Нельзя отвечать в этой теме."))

    if request.method == "POST":
        form = PostForm(request.POST, user=request.user)
        upload_files = request.FILES.getlist("attachments")
        reply_list_page = request.POST.get("reply_page") or request.GET.get("page", 1)

        if form.is_valid():
            try:
                # Проверка вложений до сохранения поста в БД
                if upload_files:
                    validate_attachment_list(upload_files)
            except forms.ValidationError as exc:
                err_msg = " ".join(exc.messages) if exc.messages else str(exc)
                messages.error(request, err_msg)
                return render(
                    request,
                    "forum/theme_detail.html",
                    build_topic_detail_context(
                        request,
                        category,
                        topic,
                        count_views=False,
                        reply_form=form,
                        page_number=reply_list_page,
                        reply_submit_failed=True,
                    ),
                )
            else:
                allowed, err = allow_user_post(request.user)

                if not allowed:
                    messages.error(request, err)
                    return render(
                        request,
                        "forum/theme_detail.html",
                        build_topic_detail_context(
                            request,
                            category,
                            topic,
                            count_views=False,
                            reply_form=form,
                            page_number=reply_list_page,
                            reply_submit_failed=True,
                        ),
                    )
                if is_duplicate_recent_post(request.user, topic.id, form.cleaned_data["content"]):
                    messages.error(request, _("Дубликат сообщения."))
                    return render(
                        request,
                        "forum/theme_detail.html",
                        build_topic_detail_context(
                            request,
                            category,
                            topic,
                            count_views=False,
                            reply_form=form,
                            page_number=reply_list_page,
                            reply_submit_failed=True,
                        ),
                    )
                post = form.save(commit=False)
                post.topic = topic
                post.author = request.user
                post.save()

                try:
                    save_post_attachments(post, upload_files)
                except Exception as exc:
                    messages.warning(request, _("Вложения не сохранены: %(err)s") % {"err": exc})
                topic.updated_at = timezone.now()
                topic.save(update_fields=["updated_at"])
                record_user_post(request.user)
                notify_topic_subscribers_new_post(topic=topic, post=post, author=request.user)
                # @упоминания в тексте ответа; автора из получателей исключаем
                notify_mentions(
                    body=post.content,
                    actor=request.user,
                    topic=topic,
                    post=post,
                    exclude_user_ids={request.user.id},
                )
                return redirect(post.get_absolute_url())
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "errors": form.errors}, status=400)
            return render(
                request,
                "forum/theme_detail.html",
                build_topic_detail_context(
                    request,
                    category,
                    topic,
                    count_views=False,
                    reply_form=form,
                    page_number=reply_list_page,
                    reply_submit_failed=True,
                ),
            )
    else:
        form = PostForm(user=request.user)

    # Ответ для AJAX-отправки формы с тем же URL, что и при обычном редиректе
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        if not form.is_bound:
            return JsonResponse({"status": "success", "redirect": topic.get_absolute_url()})

        if form.errors:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
        return JsonResponse(
            {
                "status": "success",
                "redirect": reverse(
                    "forum:topic_detail",
                    kwargs={"category_slug": category.slug, "topic_slug": topic.slug},
                ),
            }
        )

    return redirect(
        "forum:topic_detail",
        category_slug=category.slug,
        topic_slug=topic.slug,
    )


@login_required
@ratelimit(key="user", rate="180/m", method="POST", block=False)
def like_post(request, post_id):
    if getattr(request, "limited", False):
        return JsonResponse({"status": "error", "reason": "ratelimit"}, status=429)
    post = get_object_or_404(Post, id=post_id)

    # Лайки только для «живых» сущностей в ленте
    if post.is_removed or post.topic.is_removed:
        return JsonResponse({"status": "error"}, status=400)
    user = request.user

    # Переключение M2M: повторный клик снимает лайк
    if user in post.liked_by.all():
        post.liked_by.remove(user)
        liked = False

        if post.author_id != user.id:
            User.objects.filter(pk=post.author_id).update(karma=F("karma") - 1)
    else:
        post.liked_by.add(user)
        liked = True

        if post.author_id != user.id:
            User.objects.filter(pk=post.author_id).update(karma=F("karma") + 1)
    return JsonResponse({"status": "success", "liked": liked, "likeCount": post.get_like_count()})


@ratelimit(key="ip", rate="8/m", method="POST", block=False)
def register(request):
    if request.user.is_authenticated:
        return redirect("forum:index")

    # Защита от перебора регистраций с одного IP
    if request.method == "POST" and getattr(request, "limited", False):
        messages.error(request, _("Слишком много попыток регистрации. Подождите."))
        return redirect("forum:register")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            form.save()
            # Явная аутентификация после create_user (сессия)
            auth_user = authenticate(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
            )

            if auth_user:
                login(request, auth_user)
            return redirect("forum:index")
    else:
        form = RegisterForm()

    return render(request, "account/signup.html", {"form": form})


def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    viewer_ignores_profile = (
        request.user.is_authenticated
        and request.user.id != user.id
        and request.user.ignored_users.filter(pk=user.pk).exists()
    )

    if viewer_ignores_profile:
        topics = Topic.objects.none()
        posts = Post.objects.none()
    else:
        topics = Topic.objects.filter(author=user).select_related("category").order_by("-created_at")[:5]
        posts = Post.objects.filter(author=user, is_removed=False).order_by("-created_at")[:5]

    dm_preview = None
    if request.user.is_authenticated and request.user.id == user.id:
        dm_preview = get_dm_inbox_summaries(user, limit=12)

    return render(
        request,
        "forum/user_profile.html",
        {
            "profile_user": user,
            "topics": topics,
            "posts": posts,
            "dm_preview": dm_preview,
            "viewer_ignores_profile": viewer_ignores_profile,
        },
    )


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = ForumUserEditForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            form.save()
            return redirect("forum:user_profile", username=request.user.username)
    else:
        form = ForumUserEditForm(instance=request.user)

    return render(request, "forum/edit_profile.html", {"form": form})


@ratelimit(key="ip", rate="90/m", method="GET", block=False)
def search(request):
    # Тяжёлый поиск — ограничение частоты с одного IP
    if getattr(request, "limited", False):
        messages.error(request, _("Слишком частые запросы поиска. Подождите."))
        return render(request, "forum/search_results.html", {"query": "", "results": []})

    query = request.GET.get("q", "")
    results = []

    if query:
        # forum_search сам выбирает стратегию под СУБД
        topics, posts = forum_search(query)
        ign = ignored_user_ids(request.user)

        if ign and not can_moderate(request.user):
            topics = [t for t in topics if t.author_id not in ign]
            posts = [p for p in posts if p.author_id not in ign]
        results = {"topics": topics, "posts": posts}
    return render(request, "forum/search_results.html", {"query": query, "results": results})


def tag_cloud(request):
    tags = (
        Tag.objects.annotate(topic_count=Count("topics"))
        .filter(topic_count__gt=0)
        .order_by("-topic_count", "name")
    )
    return render(request, "forum/tag_cloud.html", {"tags": tags})


def tag_detail(request, tag_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)
    topics = filter_topics_for_viewer(
        Topic.objects.filter(tags=tag).select_related("category", "author").order_by("-updated_at"),
        request.user,
    )
    paginator = Paginator(topics, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return render(request, "forum/tag_topics.html", {"tag": tag, "page_obj": page_obj})


# --- Редактирование и удаление ---


@login_required
def edit_topic(request, category_slug, topic_slug):
    category = get_object_or_404(Category, slug=category_slug)
    topic = Topic.get_for_view(request.user, category_slug, topic_slug)

    if not topic or topic.category_id != category.id:
        return HttpResponseForbidden(_("Нет доступа."))

    if not can_edit_topic(request.user, topic):
        return HttpResponseForbidden(_("Нельзя редактировать тему."))

    first = topic.first_post()

    if request.method == "POST":
        form = TopicEditForm(request.POST, instance=topic)

        if form.is_valid():
            # Снимок для истории правок и синхронизация текста первого поста с телом темы
            old_title = topic.title
            old_content = topic.content
            new_title = form.cleaned_data["title"]
            new_content = form.cleaned_data["content"]
            reason = form.cleaned_data.get("edit_reason") or ""

            if old_title != new_title or old_content != new_content:
                # Запись снимка только при реальном изменении
                TopicRevision.objects.create(
                    topic=topic,
                    editor=request.user,
                    old_title=old_title,
                    new_title=new_title,
                    old_content=old_content,
                    new_content=new_content,
                    edit_reason=reason,
                )
            topic.title = new_title
            topic.content = new_content
            topic.save(update_fields=["title", "content", "updated_at"])
            sync_topic_tags_from_string(topic, form.cleaned_data.get("tags", ""))

            if first:
                if first.content != new_content:
                    PostRevision.objects.create(
                        post=first,
                        editor=request.user,
                        old_content=first.content,
                        new_content=new_content,
                        edit_reason=reason,
                    )
                    first.content = new_content
                    first.save(update_fields=["content", "updated_at"])
            messages.success(request, _("Тема обновлена."))
            return redirect(topic.get_absolute_url())
    else:
        form = TopicEditForm(instance=topic)

    return render(
        request,
        "forum/topic_edit.html",
        {"form": form, "topic": topic, "category": category},
    )


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if not can_edit_post(request.user, post):
        return HttpResponseForbidden(_("Нельзя редактировать сообщение."))

    if post.is_removed or post.topic.is_removed:
        return HttpResponseForbidden(_("Сообщение недоступно."))

    if request.method == "POST":
        form = PostEditForm(request.POST, instance=post)
        upload_files = request.FILES.getlist("attachments")

        if form.is_valid():
            try:
                if upload_files:
                    validate_attachment_list(upload_files)
            except forms.ValidationError as exc:
                err_msg = " ".join(exc.messages) if exc.messages else str(exc)
                messages.error(request, err_msg)
            else:
                # История правок хранит только изменение текста
                old = post.content
                new = form.cleaned_data["content"]
                reason = form.cleaned_data.get("edit_reason") or ""

                if old != new:
                    PostRevision.objects.create(
                        post=post,
                        editor=request.user,
                        old_content=old,
                        new_content=new,
                        edit_reason=reason,
                    )
                form.save()

                try:
                    save_post_attachments(post, upload_files)
                except forms.ValidationError as exc:
                    messages.warning(
                        request,
                        " ".join(exc.messages) if hasattr(exc, "messages") else str(exc),
                    )
                messages.success(request, _("Сообщение сохранено."))
                return redirect(post.get_absolute_url())
    else:
        form = PostEditForm(instance=post)

    return render(
        request,
        "forum/post_edit.html",
        {"form": form, "post": post, "topic": post.topic, "category": post.topic.category},
    )


@login_required
def soft_delete_topic(request, category_slug, topic_slug):
    topic = Topic.all_objects.filter(slug=topic_slug, category__slug=category_slug).first()

    if not topic:
        return HttpResponseForbidden(_("Тема не найдена."))

    if not can_delete_topic(request.user, topic):
        return HttpResponseForbidden(_("Нельзя удалить тему."))

    if request.method == "POST":
        form = SoftDeleteForm(request.POST)

        if form.is_valid():
            # Мягкое удаление: запись остаётся в БД для модерации и истории
            reason = form.cleaned_data.get("reason") or ""
            topic.is_removed = True
            topic.removed_at = timezone.now()
            topic.removed_by = request.user
            topic.removal_reason = reason
            topic.save(update_fields=["is_removed", "removed_at", "removed_by", "removal_reason", "updated_at"])
            messages.success(request, _("Тема удалена (скрыта с сайта)."))
            return redirect("forum:category_detail", slug=topic.category.slug)
    else:
        form = SoftDeleteForm()

    return render(
        request,
        "forum/topic_delete_confirm.html",
        {"form": form, "topic": topic, "category": topic.category},
    )


@login_required
def soft_delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if not can_delete_post(request.user, post):
        return HttpResponseForbidden(_("Нельзя удалить сообщение."))

    if post.is_removed:
        return redirect(post.topic.get_absolute_url())

    if request.method == "POST":
        form = SoftDeleteForm(request.POST)

        if form.is_valid():
            reason = form.cleaned_data.get("reason") or ""
            # Мягкое удаление поста — цепочка в теме сохраняет отступы по id
            post.is_removed = True
            post.removed_at = timezone.now()
            post.removed_by = request.user
            post.removal_reason = reason
            post.save(
                update_fields=[
                    "is_removed",
                    "removed_at",
                    "removed_by",
                    "removal_reason",
                    "updated_at",
                ]
            )
            messages.success(request, _("Сообщение удалено."))
            return redirect(post.topic.get_absolute_url())
    else:
        form = SoftDeleteForm()

    return render(
        request,
        "forum/post_delete_confirm.html",
        {"form": form, "post": post, "topic": post.topic, "category": post.topic.category},
    )


# --- Модерация ---


@login_required
def mod_toggle_sticky(request, category_slug, topic_slug):
    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))

    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    topic = get_object_or_404(Topic.all_objects, slug=topic_slug, category__slug=category_slug)
    # Флаг закрепления влияет только на сортировку в списках
    topic.is_sticky = not topic.is_sticky
    topic.save(update_fields=["is_sticky", "updated_at"])
    messages.success(request, _("Закрепление обновлено."))
    return redirect(topic.get_absolute_url())


@login_required
def mod_toggle_closed(request, category_slug, topic_slug):
    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))

    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    topic = get_object_or_404(Topic.all_objects, slug=topic_slug, category__slug=category_slug)
    # Закрытая тема не принимает ответы от обычных пользователей
    topic.is_closed = not topic.is_closed
    topic.save(update_fields=["is_closed", "updated_at"])
    messages.success(request, _("Статус «закрыта» обновлён."))
    return redirect(topic.get_absolute_url())


@login_required
def mod_move_topic(request, category_slug, topic_slug):
    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    topic = get_object_or_404(Topic.all_objects, slug=topic_slug, category__slug=category_slug)

    if request.method == "POST":
        form = MoveTopicForm(request.POST)

        if form.is_valid():
            new_cat = form.cleaned_data["category"]
            topic.category = new_cat
            # Slug пересчитываем в новой категории (уникальность в паре category+slug)
            topic.slug = topic.make_unique_slug(topic.title)
            topic.save(update_fields=["category", "slug", "updated_at"])
            messages.success(request, _("Тема перенесена."))
            return redirect(
                "forum:topic_detail",
                category_slug=new_cat.slug,
                topic_slug=topic.slug,
            )
    else:
        form = MoveTopicForm(initial={"category": topic.category})

    return render(
        request,
        "forum/mod_move_topic.html",
        {"form": form, "topic": topic, "category": topic.category},
    )


@login_required
def mod_hide_post(request, post_id):
    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        form = HidePostForm(request.POST)

        if form.is_valid():
            # Скрытое сообщение остаётся у модераторов в ленте темы
            post.is_hidden = True
            post.hidden_at = timezone.now()
            post.hidden_by = request.user
            post.hidden_reason = form.cleaned_data["reason"]
            post.save(update_fields=["is_hidden", "hidden_at", "hidden_by", "hidden_reason", "updated_at"])
            messages.success(request, _("Сообщение скрыто."))
            return redirect(post.topic.get_absolute_url())
    else:
        form = HidePostForm()

    return render(
        request,
        "forum/mod_hide_post.html",
        {"form": form, "post": post, "topic": post.topic},
    )


@login_required
def mod_unhide_post(request, post_id):
    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))

    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    post = get_object_or_404(Post, id=post_id)
    # Сброс полей скрытия для публичного отображения
    post.is_hidden = False
    post.hidden_at = None
    post.hidden_by = None
    post.hidden_reason = ""
    post.save(update_fields=["is_hidden", "hidden_at", "hidden_by", "hidden_reason", "updated_at"])
    messages.success(request, _("Сообщение снова видно."))
    return redirect(post.topic.get_absolute_url())


@login_required
def mod_reports(request):
    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    # Очередь жалоб «к обработке»
    qs = ContentReport.objects.filter(status=ContentReport.STATUS_PENDING).select_related(
        "reporter", "topic", "post", "reported_user"
    )
    return render(request, "forum/mod_reports.html", {"reports": qs})


@login_required
def mod_report_resolve(request, report_id):
    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    report = get_object_or_404(ContentReport, id=report_id)

    if request.method == "POST":
        # Закрываем жалобу с фиксацией модератора и опциональной заметкой
        report.status = ContentReport.STATUS_RESOLVED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.moderator_note = request.POST.get("note", "")
        report.save()
        messages.success(request, _("Жалоба отмечена как рассмотренная."))
    return redirect("forum:mod_reports")


@login_required
def mod_report_dismiss(request, report_id):
    if not can_moderate(request.user):
        return HttpResponseForbidden(_("Недостаточно прав."))
    report = get_object_or_404(ContentReport, id=report_id)

    if request.method == "POST":
        # Жалоба без мер — отклонена, но остаётся в истории
        report.status = ContentReport.STATUS_DISMISSED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.moderator_note = request.POST.get("note", "")
        report.save()
        messages.success(request, _("Жалоба отклонена."))
    return redirect("forum:mod_reports")


# --- Подписки и уведомления ---


@login_required
def topic_subscribe(request, category_slug, topic_slug):
    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))
    topic = get_object_or_404(Topic, slug=topic_slug, category__slug=category_slug)
    TopicSubscription.objects.get_or_create(user=request.user, topic=topic)
    messages.success(request, _("Вы подписаны на тему."))
    return redirect(topic.get_absolute_url())


@login_required
def topic_unsubscribe(request, category_slug, topic_slug):
    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))
    topic = get_object_or_404(Topic, slug=topic_slug, category__slug=category_slug)
    TopicSubscription.objects.filter(user=request.user, topic=topic).delete()
    messages.success(request, _("Подписка отменена."))
    return redirect(topic.get_absolute_url())


@login_required
def notifications_list(request):
    qs = Notification.objects.filter(recipient=request.user)[:100]
    return render(request, "forum/notifications.html", {"items": qs})


@login_required
def notification_mark_read(request, notification_id):
    n = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    n.read_at = timezone.now()
    n.save(update_fields=["read_at"])

    # Клик по уведомлению ведёт на целевую страницу, если ссылка задана
    if n.link:
        return redirect(n.link)
    return redirect("forum:notifications")


@login_required
def notification_mark_all_read(request):
    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))
    # Одним запросом помечаем все непрочитанные
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    messages.success(request, _("Все отмечены прочитанными."))
    return redirect("forum:notifications")


# --- Жалобы ---


@login_required
def report_topic(request, category_slug, topic_slug):
    topic = get_object_or_404(Topic, slug=topic_slug, category__slug=category_slug)

    if request.method == "POST":
        form = ContentReportForm(request.POST)

        if form.is_valid():
            # Очередь модерации + уведомления модераторам (in-app и email по настройкам профиля)
            rep = ContentReport.objects.create(
                reporter=request.user,
                topic=topic,
                reason=form.cleaned_data["reason"],
            )
            notify_moderators_new_report(rep)
            messages.success(request, _("Жалоба отправлена."))
            return redirect(topic.get_absolute_url())
    else:
        form = ContentReportForm()
    return render(request, "forum/report_form.html", {"form": form, "topic": topic})


@login_required
def report_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        form = ContentReportForm(request.POST)

        if form.is_valid():
            # Жалоба привязана и к посту, и к теме для контекста в админке
            rep = ContentReport.objects.create(
                reporter=request.user,
                post=post,
                topic=post.topic,
                reason=form.cleaned_data["reason"],
            )
            notify_moderators_new_report(rep)
            messages.success(request, _("Жалоба отправлена."))
            return redirect(post.get_absolute_url())
    else:
        form = ContentReportForm()
    return render(request, "forum/report_form.html", {"form": form, "topic": post.topic, "post": post})


# --- Личные сообщения ---


@login_required
def dm_inbox(request):
    inbox_rows = get_dm_inbox_summaries(request.user)
    return render(request, "forum/dm_inbox.html", {"inbox_rows": inbox_rows})


@login_required
def dm_thread(request, thread_id):
    part = PrivateThreadParticipant.objects.filter(user=request.user, thread_id=thread_id).first()

    if not part:
        return HttpResponseForbidden(_("Нет доступа к переписке."))
    thread = part.thread
    other_part = thread.participants.exclude(user=request.user).first()

    if other_part and users_block_dm(request.user, other_part.user):
        return HttpResponseForbidden(_("Переписка недоступна из-за настроек игнора."))

    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()

        if body:
            # Исходящее сообщение в открытом треде + уведомление второму участнику
            PrivateMessage.objects.create(thread=thread, sender=request.user, body=body)
            thread.updated_at = timezone.now()
            thread.save(update_fields=["updated_at"])
            other = thread.participants.exclude(user=request.user).first()

            if other:
                link_path = reverse("forum:dm_thread", kwargs={"thread_id": thread.id})
                Notification.objects.create(
                    recipient=other.user,
                    actor=request.user,
                    notification_type=Notification.TYPE_PM,
                    message=_("Новое сообщение от %(username)s") % {"username": request.user.username},
                    link=link_path,
                )
                try_email_pm(other.user, request.user.username, link_path)
            messages.success(request, _("Отправлено."))
        return redirect("forum:dm_thread", thread_id=thread.id)

    thread_messages = thread.messages.select_related("sender").all()
    # Просмотр треда помечает «прочитано» на текущий момент
    part.last_read_at = timezone.now()
    part.save(update_fields=["last_read_at"])
    # Уведомления «ЛС» с ссылкой на этот тред — тоже прочитаны (как после клика по колокольчику)
    mark_pm_notifications_read_for_thread(request.user, thread.id)
    return render(request, "forum/dm_thread.html", {"thread": thread, "thread_messages": thread_messages})


@login_required
def dm_compose(request, username=None):
    other = None

    if username:
        other = get_object_or_404(User, username=username)

    if request.method == "POST":
        form = PrivateMessageComposeForm(request.POST)

        if form.is_valid():
            uname = form.cleaned_data["to_username"]

            try:
                other_u = User.objects.get(username__iexact=uname.strip())
            except User.DoesNotExist:
                messages.error(request, _("Пользователь не найден."))
            else:
                # Создаём или находим DM-тред и пишем первое сообщение в нём
                if other_u.id == request.user.id:
                    messages.error(request, _("Нельзя написать самому себе."))
                else:
                    try:
                        thread = get_or_create_dm_thread(request.user, other_u)[0]
                    except ValueError as exc:
                        messages.error(request, str(exc))
                    else:
                        PrivateMessage.objects.create(
                            thread=thread,
                            sender=request.user,
                            body=form.cleaned_data["message"],
                        )
                        thread.updated_at = timezone.now()
                        thread.save(update_fields=["updated_at"])
                        link_path = reverse("forum:dm_thread", kwargs={"thread_id": thread.id})
                        Notification.objects.create(
                            recipient=other_u,
                            actor=request.user,
                            notification_type=Notification.TYPE_PM,
                            message=_("Новое сообщение от %(username)s") % {"username": request.user.username},
                            link=link_path,
                        )
                        try_email_pm(other_u, request.user.username, link_path)
                        messages.success(request, _("Сообщение отправлено."))
                        return redirect("forum:dm_thread", thread_id=thread.id)
    else:
        initial = {}

        if other:
            initial["to_username"] = other.username
        form = PrivateMessageComposeForm(initial=initial)

    return render(request, "forum/dm_compose.html", {"form": form, "reply_to": other})


# --- Закладки, опросы, игнор ---


@login_required
def bookmarks_list(request):
    bookmarks = (
        TopicBookmark.objects.filter(user=request.user)
        .select_related("topic", "topic__category")
        .order_by("-created_at")
    )
    paginator = Paginator(bookmarks, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return render(request, "forum/bookmarks.html", {"page_obj": page_obj})


@login_required
def topic_bookmark_toggle(request, category_slug, topic_slug):
    topic = get_object_or_404(Topic, slug=topic_slug, category__slug=category_slug)

    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))
    bm, created = TopicBookmark.objects.get_or_create(user=request.user, topic=topic)

    if not created:
        bm.delete()
        messages.success(request, _("Закладка удалена."))
    else:
        messages.success(request, _("Тема добавлена в закладки."))
    return redirect(topic.get_absolute_url())


@login_required
def poll_vote_submit(request, category_slug, topic_slug):
    topic = Topic.get_for_view(request.user, category_slug, topic_slug)

    if not topic or topic.category.slug != category_slug:
        raise Http404(_("Тема не найдена."))
    poll = getattr(topic, "poll", None)

    if not poll or topic.is_closed or request.method != "POST":
        return redirect(topic.get_absolute_url())
    existing = PollVote.objects.filter(poll=poll, user=request.user).first()

    if existing:
        messages.info(request, _("Вы уже голосовали в этом опросе."))
        return redirect(topic.get_absolute_url())
    form = PollVoteForm(poll, request.POST)

    if form.is_valid():
        PollVote.objects.create(
            poll=poll,
            user=request.user,
            option=form.cleaned_data["option"],
        )
        messages.success(request, _("Голос учтён."))
    else:
        messages.error(request, _("Не удалось сохранить голос."))
    return redirect(topic.get_absolute_url())


@login_required
def toggle_ignore_user(request, username):
    other = get_object_or_404(User, username=username)

    if other.pk == request.user.pk:
        messages.error(request, _("Нельзя игнорировать самого себя."))
        return redirect("forum:user_profile", username=username)

    if request.method != "POST":
        return HttpResponseForbidden(_("Только POST."))

    if request.user.ignored_users.filter(pk=other.pk).exists():
        request.user.ignored_users.remove(other)
        messages.success(request, _("Пользователь снят с игнора."))
    else:
        request.user.ignored_users.add(other)
        messages.success(request, _("Пользователь добавлен в игнор."))
    return redirect("forum:user_profile", username=username)


@login_required
def manage_ignored_users(request):
    if request.method == "POST":
        form = IgnoredUsersManageForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
            messages.success(request, _("Список игнора обновлён."))
            return redirect("forum:manage_ignored_users")
    else:
        form = IgnoredUsersManageForm(instance=request.user)

    return render(request, "forum/manage_ignored.html", {"form": form})


# --- История правок ---


def topic_revision_history(request, category_slug, topic_slug):
    topic = Topic.get_for_view(request.user, category_slug, topic_slug)

    # Удалённую тему без прав модерации не показываем даже историю
    if not topic:
        return HttpResponseForbidden(_("Нет доступа."))
    revs = topic.revisions.select_related("editor").all()[:50]
    return render(
        request,
        "forum/topic_revisions.html",
        {"topic": topic, "category": topic.category, "revisions": revs},
    )


def post_revision_history(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    # Скрываем историю постов в мягко удалённой теме от обычных пользователей
    if post.topic.is_removed and not can_moderate(request.user):
        return HttpResponseForbidden(_("Нет доступа."))
    revs = post.revisions.select_related("editor").all()[:50]
    return render(
        request,
        "forum/post_revisions.html",
        {"post": post, "topic": post.topic, "category": post.topic.category, "revisions": revs},
    )
