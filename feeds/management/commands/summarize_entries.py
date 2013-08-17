from django.core.management.base import BaseCommand, CommandError
from feeds.models import Entry

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        while Entry.objects.filter(summarized=False).count() > 0:
            entry = Entry.objects.filter(summarized=False)[0]
            entry.summarize("lxml")
