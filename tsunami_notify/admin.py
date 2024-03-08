from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from django_admin_listfilter_dropdown.filters import DropdownFilter

from rangefilter.filters import DateRangeFilter

from .models import Notification


class IsSentFilter(admin.EmptyFieldListFilter):
    """
    Filter for sent/not sent.
    """
    def choices(self, changelist):
        # Just customise the option names
        for lookup, title in (
            (None, 'All'),
            ('0', 'Sent'),
            ('1', 'Not sent'),
        ):
            yield {
                'selected': self.lookup_val == lookup,
                'query_string': changelist.get_query_string({self.lookup_kwarg: lookup}),
                'display': title,
            }


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'email',
        'event_short_id_link',
        'event_type_formatted',
        'sent_at',
        'created_at',
    )
    list_select_related = ('event', )
    list_filter = (
        ('event__event_type', DropdownFilter),
        ('sent_at', IsSentFilter),
        ('sent_at', DateRangeFilter),
    )
    search_fields = ('email', 'event__event_type')
    # There could be many events, so use a raw id field to avoid looking them all up
    raw_id_fields = ('event', )

    actions = ('send_notifications', )

    def event_short_id_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                'admin:tsunami_event_change',
                args = (obj.event.id, )
            ),
            obj.event.short_id
        )
    event_short_id_link.short_description = 'event short id'

    def event_type_formatted(self, obj):
        return format_html('<code>{}</code>', obj.event.event_type)
    event_type_formatted.short_description = 'event type'

    def send_notifications(self, request, queryset):
        """
        Action method to send all the notifications in the given queryset.
        """
        [num_succeeded, num_failed] = queryset.send_all()
        if num_succeeded:
            self.message_user(
                request,
                '{} notification(s) sent.'.format(num_succeeded),
                messages.SUCCESS
            )
        if num_failed:
            self.message_user(
                request,
                '{} notification(s) failed to send (see logs for details).'.format(num_failed),
                messages.ERROR
            )
    send_notifications.short_description = 'Send selected notifications'
    send_notifications.allowed_permissions = ('change', )
