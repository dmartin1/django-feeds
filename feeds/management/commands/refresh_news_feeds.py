from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Scrape the Feeds
        call_command('scrape_feeds', args, kwargs)
        
        # Summarize the Entries
        call_command('summarize_entries', args, kwargs)