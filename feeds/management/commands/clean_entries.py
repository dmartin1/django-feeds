from datetime import timedelta
from optparse import make_option
from subprocess import call

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now
from feeds.models import Entry


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--max-count',
            type="int",
            nargs=1,
            default=None,
            help='Maximum number of entries to keep'),
        make_option('--max-age',
            type="int",
            nargs=1,
            default=None,
            help='Maximum age of entries in days in days.'),
    )
    
    def handle(self, *args, **kwargs):
        max_entries = kwargs.get('max_entries', None)
        max_age     = kwargs.get('max_age', None)
        
        if max_entries == None and max_age == None:
            raise CommandError("Either max_entries or max_age must be supplied.")
        
        if max_entries >= 0:
            Entry.objects.all()[max_entries:].delete()
        
        if max_age >= 0:
            Entry.objects.filter(published__lt=now() - timedelta(days=max_age)).delete()
