from django.core.management.base import BaseCommand, CommandError

from ...models import Notification


class Command(BaseCommand):
    """
    Sends all the currently unsent notifications.
    """
    help = "Send all notifications that have not previously been sent."

    def handle(self, *args, **options):
        # Just get all the unsent notifications and send them
        [num_succeeded, num_failed] = Notification.objects.filter_unsent().send_all()
        if num_succeeded or not num_failed:
            self.stdout.write(
                self.style.SUCCESS("{} notification(s) sent.".format(num_succeeded))
            )
        if num_failed:
            raise CommandError(
                "{} notification(s) failed to send.".format(num_failed)
            )
