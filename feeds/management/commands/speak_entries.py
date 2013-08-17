from datetime import timedelta
from optparse import make_option
from subprocess import call

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now
from feeds.models import Entry


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--max-entries',
            type="int",
            nargs=1,
            help='Maximum number of entries to read aloud'),
        make_option('--destination',
            type="string",
            nargs=1,
            help='Desination audio device'),
    )
    
    def handle(self, *args, **kwargs):
        max_entries   = kwargs.get('max_entries', 0)
        destination = kwargs.get('destination', None) or "Built-in Output"
        
        spoken_entry_count = 0
        while (
            Entry.objects.filter(spoken=False).count() > 0 and
            spoken_entry_count == 0 or spoken_entry_count <= max_entries
        ):
            entry = Entry.objects.filter(spoken=False)[0]
            call(["say", "-a", '%s' % (destination,), "Next"])
            entry.speak_aloud(destination)
