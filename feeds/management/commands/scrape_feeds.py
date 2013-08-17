from django.core.management.base import BaseCommand, CommandError
from feeds.models import Feed

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for feed in Feed.objects.all():
            try:
                feed.update()
            except:
                pass
