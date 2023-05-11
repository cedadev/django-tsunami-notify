import time

import django.core.management.base

from ...models import Notification


class Command(django.core.management.base.BaseCommand):
    """Sends all the currently unsent notifications."""

    help = "Send all notifications that have not previously been sent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run_forever",
            action="store_true",
            help="Run the sender forever in a loop instead of exiting when notificaitons are sent.",
        )

    def handle(self, *args, **options):
        """Get all the unsent notifications and send them."""
        while True:
            [
                num_succeeded,
                num_failed,
            ] = Notification.objects.filter_unsent().send_all()

            if num_succeeded:
                self.stdout.write(
                    self.style.SUCCESS(f"{num_succeeded} notification(s) sent.")
                )

            if num_failed:
                self.stdout.write(
                    self.style.ERROR(f"{num_failed} notification(s) failed to send.")
                )

            if not options["run_forever"]:
                break

            time.sleep(60)
