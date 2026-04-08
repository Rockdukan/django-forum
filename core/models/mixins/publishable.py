from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PublishableMixin(models.Model):
    """
    Mixin for managing object publication status.

    Adds fields and methods for managing publication status,
    publication date and object visibility.
    """
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("scheduled", _("Scheduled")),
        ("published", _("Published")),
        ("archived", _("Archived")),
        ("failed", _("Failed")),
    ]

    status = models.CharField(_("Status"), choices=STATUS_CHOICES, default="draft", max_length=20)
    published_at = models.DateTimeField(
        _("Publication date"), blank=True, db_index=True, help_text=_("Object publication date"), null=True
    )
    scheduled_at = models.DateTimeField(
        _("Scheduled for"), blank=True, db_index=True, help_text=_("Scheduled publication date and time"), null=True
    )

    class Meta:
        abstract = True

    def publish(self, commit=True):
        """
        Publishes the object.

        Sets status to "published" and publication date.

        Args:
            commit: Whether to save changes to the database.
                Defaults to True.
        """
        self.status = "published"

        if not self.published_at:
            self.published_at = timezone.now()

        self.scheduled_at = None

        if commit:
            self.save()

    def unpublish(self, commit=True):
        """
        Unpublishes the object.

        Sets status to "draft".

        Args:
            commit: Whether to save changes to the database.
                Defaults to True.
        """
        self.status = "draft"
        self.scheduled_at = None

        if commit:
            self.save()

    def archive(self, commit=True):
        """
        Archives the object.

        Sets status to "archived".

        Args:
            commit: Whether to save changes to the database.
                Defaults to True.
        """
        self.status = "archived"
        self.scheduled_at = None

        if commit:
            self.save()

    def schedule(self, scheduled_date=None, commit=True):
        """
        Schedules the object for publication.

        Sets status to "scheduled" and scheduled_at date.

        Args:
            scheduled_date: Scheduled publication date and time.
                If not specified, current time is used.
            commit: Whether to save changes to the database.
                Defaults to True.
        """
        self.status = "scheduled"
        self.scheduled_at = scheduled_date or timezone.now()

        if commit:
            self.save()

    def mark_as_failed(self, commit=True):
        """
        Marks the object as failed.

        Sets status to "failed".

        Args:
            commit: Whether to save changes to the database.
                Defaults to True.
        """
        self.status = "failed"
        self.scheduled_at = None

        if commit:
            self.save()

    def is_published(self):
        """
        Checks if the object is published.

        Returns:
            True if object status is "published", False otherwise.
        """
        return self.status == "published"

    def is_scheduled(self):
        """
        Checks if the object is scheduled for publication.

        Returns:
            True if object status is "scheduled", False otherwise.
        """
        return self.status == "scheduled"

    def is_draft(self):
        """
        Checks if the object is a draft.

        Returns:
            True if object status is "draft", False otherwise.
        """
        return self.status == "draft"

    def is_ready_to_publish(self):
        """
        Checks if the scheduled object is ready to be published.

        Returns:
            True if object is scheduled and scheduled_at time has passed,
            False otherwise.
        """
        if self.status == "scheduled" and self.scheduled_at:
            return self.scheduled_at <= timezone.now()
        return False

    def auto_publish_if_ready(self, commit=True):
        """
        Automatically publishes the object if it's ready.

        Checks if the object is scheduled and the scheduled time has passed.
        If so, publishes the object.

        Args:
            commit: Whether to save changes to the database.
                Defaults to True.

        Returns:
            True if object was published, False otherwise.
        """
        if self.is_ready_to_publish():
            self.publish(commit=commit)
            return True
        return False
