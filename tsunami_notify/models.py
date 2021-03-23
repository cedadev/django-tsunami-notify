import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import get_connection, send_mail
from django.db import models
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone

from jsonfield import JSONField

from tsunami.models import Event


logger = logging.getLogger(__name__)


class NotificationQuerySet(models.QuerySet):
    """
    Query set for notifications that allows all notifications in a queryset
    to be sent using the same connection.
    """
    def filter_unsent(self):
        """
        Returns a queryset with only the unsent notifications in it.
        """
        return self.filter(sent_at__isnull = True)

    def send_all(self):
        """
        Sends all the notifications in the queryset using a single SMTP connection.

        Returns a two-tuple of (num notifications sent, num notifications failed).
        """
        num_succeeded = num_failed = 0
        with get_connection() as connection:
            for notification in self:
                try:
                    notification.send(connection)
                except:
                    logger.exception(
                        "Error sending notification with ID '{}'".format(notification.id)
                    )
                    num_failed += 1
                else:
                    num_succeeded += 1
        return [num_succeeded, num_failed]


class Notification(models.Model):
    """
    Model for a notification that is associated with an event.
    """
    #: The Tsunami event that triggered the notification
    event = models.ForeignKey(Event, models.CASCADE)
    #: The email address that the notification should be sent to
    email = models.EmailField()
    #: The template context for rendering email content
    context = JSONField(default = dict)
    #: The time at which the notification was last sent
    sent_at = models.DateTimeField(null = True)
    #: The time at which the notification was created
    created_at = models.DateTimeField(auto_now_add = True)

    objects = NotificationQuerySet.as_manager()

    @classmethod
    def create(cls, event, email, context = None):
        """
        Create a new notification.
        """
        return cls.objects.create(
            event = event,
            email = email,
            context = context or dict()
        )

    def get_template_directories(self):
        """
        Returns an iterable of possible template directories for the event.
        """
        # Allow directories with the full event type
        yield "tsunami_notify/{}".format(self.event.event_type)
        # Also allow for subdirectories based on dots in the event type
        event_type_parts = self.event.event_type.split(".")
        # Recombine as a directory
        event_type_subdir = os.path.join(*event_type_parts)
        # Yield the template path
        yield "tsunami_notify/{}".format(event_type_subdir)

    def render_template(self, template_name):
        """
        Renders the given template with the stored context.
        """
        # If the email address belongs to a user that we are aware of, resolve them
        recipient = get_user_model().objects.filter(email__iexact = self.email).first()
        # Build the template context
        context = dict(event = self.event, target = self.event.target, recipient = recipient)
        context.update(self.context)
        # Allow the template to come from any of the event directories
        templates = [
            os.path.join(directory, template_name)
            for directory in self.get_template_directories()
        ]
        # Render the template
        return render_to_string(templates, context)

    def send(self, connection = None):
        """
        Renders the content and sends the notification.
        """
        # Subject and plain-text message are required - let missing template errors bubble
        subject = self.render_template('subject.txt')
        message = self.render_template('message.txt')
        # The HTML message content is optional
        try:
            html_message = self.render_template('message.html')
        except TemplateDoesNotExist:
            html_message = None
        # Try to actually send the email
        send_mail(
            subject,
            message,
            # Allow a notification-specific from email to be set
            getattr(settings, 'TSUNAMI_NOTIFY_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL),
            [self.email],
            connection = connection,
            html_message = html_message
        )
        # If the email sent successfully, update the notification to reflect that
        self.sent_at = timezone.now()
        self.save()

    def get_event_type(self, diff):
        # If sent_at is in the diff, use a special event type
        if 'sent_at' in diff and diff['sent_at'] is not None:
            return '{}.sent'.format(self._meta.label_lower)
