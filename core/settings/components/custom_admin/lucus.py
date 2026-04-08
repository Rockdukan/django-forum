LUCUS_DASHBOARD = [
    {
        "column": 1,
        "title": "🧩 Содержимое сайта",
        "links": [
            {"label": "🏠 Главная", "admin_urlname": "admin:index_index_changelist"},
            {"label": "ℹ️ О нас", "admin_urlname": "admin:site_pages_aboutpage_changelist"},
            {"label": "📞 Контакты", "admin_urlname": "admin:site_pages_contactspage_changelist"},
            {"label": "🔒 Конфиденциальность", "admin_urlname": "admin:site_pages_privacypage_changelist"},
            {"label": "📜 Правила", "admin_urlname": "admin:site_pages_rulespage_changelist"},
        ],
    },
    {
        "column": 1,
        "title": "💬 Форум",
        "links": [
            {"label": "🗂️ Категории", "admin_urlname": "admin:forum_category_changelist"},
            {"label": "🧵 Темы", "admin_urlname": "admin:forum_topic_changelist"},
            {"label": "✍️ Посты", "admin_urlname": "admin:forum_post_changelist"},
            {"label": "🏷️ Теги", "admin_urlname": "admin:forum_tag_changelist"},
        ],
    },
    {
        "column": 2,
        "title": "🗄️ Медиа",
        "links": [
            {"label": "📝 Summernote: вложения", "admin_urlname": "admin:django_summernote_attachment_changelist"},
            {"label": "📎 Вложения постов", "admin_urlname": "admin:forum_postattachment_changelist"},
        ],
    },
    {
        "column": 2,
        "title": "🔔 Активность и уведомления",
        "links": [
            {"label": "🔔 Уведомления", "admin_urlname": "admin:forum_notification_changelist"},
            {"label": "⭐ Подписки на темы", "admin_urlname": "admin:forum_topicsubscription_changelist"},
            {"label": "📝 Редакции тем", "admin_urlname": "admin:forum_topicrevision_changelist"},
            {"label": "📝 Редакции постов", "admin_urlname": "admin:forum_postrevision_changelist"},
        ],
    },
    {
        "column": 3,
        "title": "👤 Аккаунты",
        "links": [
            {"label": "👥 Пользователи", "admin_urlname": "admin:users_user_changelist"},
            {"label": "👮 Группы", "admin_urlname": "admin:auth_group_changelist"},
        ],
    },
    {
        "column": 3,
        "title": "📨 Личные сообщения",
        "links": [
            {"label": "🧵 Треды", "admin_urlname": "admin:forum_privatethread_changelist"},
            {"label": "👥 Участники", "admin_urlname": "admin:forum_privatethreadparticipant_changelist"},
            {"label": "✉️ Сообщения", "admin_urlname": "admin:forum_privatemessage_changelist"},
        ],
    },
    {
        "column": 3,
        "title": "🛡️ Модерация",
        "links": [
            {"label": "🚩 Жалобы", "admin_urlname": "admin:forum_contentreport_changelist"},
        ],
    },
    {
        "column": 4,
        "title": "⚙️ Системные настройки",
        "links": [
            {"label": "🔁 Перенаправления", "admin_urlname": "admin:redirects_redirect_changelist"},
            {"label": "🗝️ Сессии", "admin_urlname": "admin:sessions_session_changelist"},
            {"label": "🌐 Сайты", "admin_urlname": "admin:sites_site_changelist"},
            {"label": "🧷 Константы", "admin_urlname": "admin:constance_config_changelist"},
        ],
    },
    {
        "column": 4,
        "title": "🤖 SEO",
        "links": [
            {"label": "🤖 Robots.txt", "admin_urlname": "admin:robots_robotstxt_changelist"},
            {"label": "🗺️ Sitemap.xml", "url": "/sitemap.xml"},
        ],
    },
    {
        "column": 4,
        "title": "🧾 Логи",
        "links": [
            {"label": "📜 Логи Django admin", "admin_urlname": "admin:admin_logentry_changelist"},
            {"label": "🧾 Логи auditlog", "admin_urlname": "admin:auditlog_auditlogentry_changelist"},
            {"label": "🧾 Auditlog: LogEntry", "url": "http://127.0.0.1:8000/cabinet/auditlog/logentry/"},
            {"label": "🪵 Log viewer", "url": "/cabinet/logs/"},
        ],
    },
]
