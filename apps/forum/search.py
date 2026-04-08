from django.db import connection
from django.db.models import Q

from .models import Post, Topic


def mysql_natural_search(topic_qs, post_qs, q: str) -> tuple[list, list]:
    """MySQL: полнотекст через MATCH … AGAINST (NATURAL LANGUAGE).

    Нужны FULLTEXT-индексы на ``forum_topic(title, content)`` и ``forum_post(content)``.
    Без них запрос падает — вызывающий код переходит на icontains.
    """
    # FULLTEXT чувствителен к синтаксису — убираем обратный слэш и короткий шум
    safe = q.replace("\\", "").strip()

    if len(safe) < 2:
        return [], []

    topics_sql = """
        SELECT id FROM forum_topic
        WHERE MATCH(title, content) AGAINST (%s IN NATURAL LANGUAGE MODE)
        ORDER BY MATCH(title, content) AGAINST (%s IN NATURAL LANGUAGE MODE) DESC, updated_at DESC
        LIMIT 50
    """
    posts_sql = """
        SELECT forum_post.id FROM forum_post
        INNER JOIN forum_topic ON forum_post.topic_id = forum_topic.id
        WHERE NOT forum_post.is_removed AND NOT forum_topic.is_removed
        AND MATCH(forum_post.content) AGAINST (%s IN NATURAL LANGUAGE MODE)
        ORDER BY MATCH(forum_post.content) AGAINST (%s IN NATURAL LANGUAGE MODE) DESC,
                 forum_post.created_at DESC
        LIMIT 50
    """
    # Сырой SQL: Django ORM не выражает MATCH … AGAINST во всех версиях одинаково
    with connection.cursor() as cursor:
        cursor.execute(topics_sql, [safe, safe])
        topic_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute(posts_sql, [safe, safe])
        post_ids = [row[0] for row in cursor.fetchall()]

    order_t = {tid: i for i, tid in enumerate(topic_ids)}
    topics = list(topic_qs.filter(pk__in=topic_ids))
    topics.sort(key=lambda t: order_t[t.pk])

    order_p = {pid: i for i, pid in enumerate(post_ids)}
    posts = list(post_qs.filter(pk__in=post_ids))
    posts.sort(key=lambda p: order_p[p.pk])
    return topics, posts


def forum_search(query: str) -> tuple[list, list]:
    """
    Поиск тем и постов.

    Notes:
        PostgreSQL: полнотекст (SearchVector / SearchQuery / SearchRank).
        MySQL: FULLTEXT через ``MATCH … AGAINST`` при наличии индексов; иначе исключение и icontains.
        Прочие СУБД (SQLite и т.д.): ``icontains``.
    """
    q = (query or "").strip()

    if len(q) < 2:
        return [], []

    # Ветвление по движку БД: полнотекст там, где он есть, иначе icontains
    vendor = connection.vendor
    topic_qs = Topic.objects.all()
    post_qs = Post.objects.filter(is_removed=False).exclude(topic__is_removed=True)

    if vendor == "postgresql":
        # contrib.postgres может быть не установлен — тогда падаем на icontains ниже
        try:
            from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

            tsq = SearchQuery(q)
            topics = (
                topic_qs.annotate(rank=SearchRank(SearchVector("title", "content"), tsq))
                .filter(rank__gt=0)
                .order_by("-rank", "-updated_at")[:50]
            )
            posts = (
                post_qs.annotate(rank=SearchRank(SearchVector("content"), tsq))
                .filter(rank__gt=0)
                .order_by("-rank", "-created_at")[:50]
            )
            return list(topics), list(posts)
        except Exception:
            pass

    if vendor == "mysql":
        # Сбои MySQL FULLTEXT не блокируют поиск — ниже будет icontains
        try:
            return mysql_natural_search(topic_qs, post_qs, q)
        except Exception:
            pass

    # Универсальный путь: регистронезависимое вхождение подстроки
    ic = q.lower()
    topics = list(topic_qs.filter(Q(title__icontains=ic) | Q(content__icontains=ic)).order_by("-updated_at")[:50])
    posts = list(post_qs.filter(content__icontains=ic).order_by("-created_at")[:50])
    return topics, posts
