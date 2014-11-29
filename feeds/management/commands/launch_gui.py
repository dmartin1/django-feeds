from django.core.management.base import BaseCommand, CommandError
from feeds.gui import FeedReaderGUI
from Tkinter import Tk

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        root = Tk()
        root.title("Feed Reader")
        app = FeedReaderGUI(master=root)
        app.mainloop()
        root.destroy()
