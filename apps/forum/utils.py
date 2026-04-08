from django.utils.text import slugify


def sync_topic_tags_from_string(topic, raw: str, *, max_tags: int = 8) -> None:
    """Парсит строку «тег1, тег2» и синхронизирует M2M темы с моделью Tag."""
    from .models import Tag

    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    tags = []
    seen_slugs: set[str] = set()
    for part in parts[:max_tags]:
        base = slugify(part)[:50] or ""
        if not base or base in seen_slugs:
            continue
        seen_slugs.add(base)
        tag, _ = Tag.objects.get_or_create(
            slug=base,
            defaults={"name": part[:50]},
        )
        tags.append(tag)
    topic.tags.set(tags)
