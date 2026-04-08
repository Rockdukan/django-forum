from django.urls import path

from . import views
from .feeds import CategoryTopicsAtomFeed, CategoryTopicsFeed, LatestTopicsAtomFeed, LatestTopicsFeed

app_name = "forum"

urlpatterns = [
    path("", views.index, name="index"),
    path("feeds/latest/", LatestTopicsFeed()),
    path("feeds/latest.atom/", LatestTopicsAtomFeed()),
    path("feeds/category/<slug:slug>/", CategoryTopicsFeed()),
    path("feeds/category/<slug:slug>.atom/", CategoryTopicsAtomFeed()),
    path("tags/", views.tag_cloud, name="tag_cloud"),
    path("tags/<slug:tag_slug>/", views.tag_detail, name="tag_detail"),
    # Старые URL /topic/<id>/ → редирект на ЧПУ
    path(
        "forum/<slug:category_slug>/topic/<int:topic_id>/",
        views.topic_legacy_redirect,
        name="topic_legacy_redirect",
    ),
    path("forum/<slug:slug>/", views.category_detail, name="category_detail"),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/",
        views.topic_detail,
        name="topic_detail",
    ),
    path("forum/<slug:category_slug>/create/", views.create_topic, name="create_topic"),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/reply/",
        views.create_post,
        name="create_post",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/edit/",
        views.edit_topic,
        name="edit_topic",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/delete/",
        views.soft_delete_topic,
        name="delete_topic",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/subscribe/",
        views.topic_subscribe,
        name="topic_subscribe",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/unsubscribe/",
        views.topic_unsubscribe,
        name="topic_unsubscribe",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/bookmark/",
        views.topic_bookmark_toggle,
        name="topic_bookmark_toggle",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/poll/vote/",
        views.poll_vote_submit,
        name="poll_vote",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/report/",
        views.report_topic,
        name="report_topic",
    ),
    path(
        "forum/<slug:category_slug>/t/<slug:topic_slug>/revisions/",
        views.topic_revision_history,
        name="topic_revisions",
    ),
    path("forum/post/<int:post_id>/edit/", views.edit_post, name="edit_post"),
    path("forum/post/<int:post_id>/delete/", views.soft_delete_post, name="delete_post"),
    path("forum/post/<int:post_id>/report/", views.report_post, name="report_post"),
    path(
        "forum/post/<int:post_id>/revisions/",
        views.post_revision_history,
        name="post_revisions",
    ),
    path("users/<str:username>/ignore/", views.toggle_ignore_user, name="toggle_ignore_user"),
    path("users/<str:username>/", views.user_profile, name="user_profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/bookmarks/", views.bookmarks_list, name="bookmarks_list"),
    path("profile/ignored/", views.manage_ignored_users, name="manage_ignored_users"),
    path("accounts/register/", views.register, name="register"),
    path("ajax/like-post/<int:post_id>/", views.like_post, name="like_post"),
    path("search/", views.search, name="search"),
    path(
        "mod/topic/<slug:category_slug>/<slug:topic_slug>/sticky/",
        views.mod_toggle_sticky,
        name="mod_toggle_sticky",
    ),
    path(
        "mod/topic/<slug:category_slug>/<slug:topic_slug>/closed/",
        views.mod_toggle_closed,
        name="mod_toggle_closed",
    ),
    path(
        "mod/topic/<slug:category_slug>/<slug:topic_slug>/move/",
        views.mod_move_topic,
        name="mod_move_topic",
    ),
    path("mod/post/<int:post_id>/hide/", views.mod_hide_post, name="mod_hide_post"),
    path("mod/post/<int:post_id>/unhide/", views.mod_unhide_post, name="mod_unhide_post"),
    path("mod/reports/", views.mod_reports, name="mod_reports"),
    path(
        "mod/reports/<int:report_id>/resolve/",
        views.mod_report_resolve,
        name="mod_report_resolve",
    ),
    path(
        "mod/reports/<int:report_id>/dismiss/",
        views.mod_report_dismiss,
        name="mod_report_dismiss",
    ),
    path("notifications/", views.notifications_list, name="notifications"),
    path(
        "notifications/<int:notification_id>/read/",
        views.notification_mark_read,
        name="notification_read",
    ),
    path(
        "notifications/read-all/",
        views.notification_mark_all_read,
        name="notifications_read_all",
    ),
    path("messages/", views.dm_inbox, name="dm_inbox"),
    path("messages/new/", views.dm_compose, name="dm_compose"),
    path(
        "messages/new/<str:username>/",
        views.dm_compose,
        name="dm_compose_to",
    ),
    path("messages/thread/<int:thread_id>/", views.dm_thread, name="dm_thread"),
]
