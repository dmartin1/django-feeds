from Tkinter import *
import ttk
import threading
import Queue
import time
import inspect
import ctypes

from optparse import make_option
from subprocess import Popen

from feeds.models import Feed
from feeds.models import Entry

# Initialize the logging library
import logging
logger = logging.getLogger(__name__)

class FeedReaderGUI(Frame):
    queue = Queue.Queue()
    
    # Threads
    thrdRefreshNewsFeeds = None
    thrdSpeakEntries = None
    
    # Responses
    STOP_REFRESH_NEWS_FEEDS = "STOP_REFRESH_NEWS_FEEDS"
    STOP_SPEAK_ENTRIES      = "STOP_SPEAK_ENTRIES"
    CONTINUE_SPEAK_ENTRIES  = "CONTINUE_SPEAK_ENTRIES"

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()
    
    def process_queue(self):
        try:
            # Show result of the task if needed
            msg = self.queue.get(0)
            logger.debug("Queue Response: %s" % (msg,))
            
            while (self.queue.qsize() > 0):
                msg = self.queue.get(0)
                logger.debug("Queue Response: %s" % (msg,))
        except Queue.Empty:
            self.after(100, self.process_queue)
    
    def exit(self):
        self.killRefreshNewsFeeds()
        self.killSpeakEntries()
        logger.debug("Shutting Down Feed Reader")
        self.quit()
    
    def createWidgets(self):
        self.QUIT = Button(self)
        self.QUIT["text"] = "Quit"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.exit
        self.QUIT.pack({"side": "left"})
        
        ## Refresh News Feeds
        self.btnRefreshNewsFeeds = Button(self)
        self.btnRefreshNewsFeeds["text"] = "Refresh",
        self.btnRefreshNewsFeeds["command"] = self.execRefreshNewsFeeds
        self.btnRefreshNewsFeeds.pack({"side": "left"})
        
        self.btnKillRefreshNewsFeeds = Button(self)
        self.btnKillRefreshNewsFeeds["text"] = "StopRefreshing",
        self.btnKillRefreshNewsFeeds["command"] = self.killRefreshNewsFeeds
        self.btnKillRefreshNewsFeeds.pack({"side": "left"})
        
        ## Speak Entries
        self.btnSpeakEntries = Button(self)
        self.btnSpeakEntries["text"] = "SpeakEntries",
        self.btnSpeakEntries["command"] = self.execSpeakEntries
        self.btnSpeakEntries.pack({"side": "left"})
        
        self.btnKillSpeakEntries = Button(self)
        self.btnKillSpeakEntries["text"] = "StopSpeaking",
        self.btnKillSpeakEntries["command"] = self.killSpeakEntries
        self.btnKillSpeakEntries.pack({"side": "left"})
        
        self.btnSkipEntry = Button(self)
        self.btnSkipEntry["text"] = "SkipEntry",
        self.btnSkipEntry["command"] = self.skipEntry
        self.btnSkipEntry.pack({"side": "left"})

    def refreshNewsFeeds(self):
        try:
            for feed in Feed.objects.all():
                try:
                    if self.thrdRefreshNewsFeeds.stopped():
                        logger.debug("Stopped refreshing")
                        self.queue.put(self.STOP_REFRESH_NEWS_FEEDS)
                        return
                    feed.update()
                except:
                    pass

            while Entry.objects.filter(summarized=False).count() > 0:
                try:
                    if self.thrdRefreshNewsFeeds.stopped():
                        logger.debug("Stopped refreshing")
                        self.queue.put(self.STOP_REFRESH_NEWS_FEEDS)
                        return
                    entry = Entry.objects.filter(summarized=False)[0]
                    entry.summarize("lxml")
                except:
                    pass
            
            self.queue.put(self.STOP_REFRESH_NEWS_FEEDS)
        finally:
            #self.queue.put(self.STOP_REFRESH_NEWS_FEEDS)
            pass
    
    def execRefreshNewsFeeds(self):
        if self.thrdRefreshNewsFeeds != None and self.thrdRefreshNewsFeeds.isAlive():
            logger.debug("Already refreshing news feeds")
            return
        logger.debug("Refreshing news feeds")
        
        self.thrdRefreshNewsFeeds = ThreadedTask(target = self.refreshNewsFeeds)
        self.thrdRefreshNewsFeeds.start()
        self.after(100, self.process_queue)
    
    def killRefreshNewsFeeds(self):
        if self.thrdRefreshNewsFeeds == None or not self.thrdRefreshNewsFeeds.isAlive():
            logger.debug("Not currently refreshing news feeds")
            return
        logger.debug("Stopping the refresh news feeds process")
        self.thrdRefreshNewsFeeds.stop()
        self.thrdRefreshNewsFeeds.join()
    
    
    ## Speak entries
    def speakEntries(self):
        process = None
        try:
            kwargs = {}
            max_entries = kwargs.get('max_entries', 0)
            #destination = kwargs.get('destination', None) or "Built-in Output"
        
            spoken_entry_count = 0
            while (
                Entry.objects.filter(spoken=False).count() > 0 and
                spoken_entry_count == 0 or spoken_entry_count <= max_entries
            ):
                
                entry = Entry.objects.filter(spoken=False, summarized=True)[0]
                process = Popen(["say", "Next"])
                logger.debug("Next...")
                while process.poll() == None:
                    if self.thrdSpeakEntries.stopped():
                        self.queue.put(self.STOP_SPEAK_ENTRIES)
                        process.terminate()
                        return
                    
                    time.sleep(0.1)
                
                logger.debug("Speaking %s from %s" % (entry.title, entry.feed.name))
                field_names = entry.feed.speech_fields.values_list('name', flat=True)
                for field_name in field_names:
                    process = Popen(["say", getattr(entry, field_name)])
                    while process.poll() == None:
                        if self.thrdSpeakEntries.stopped():
                            self.queue.put(self.STOP_SPEAK_ENTRIES)
                            process.terminate()
                            return
                        
                        if self.thrdSpeakEntries.getContinue():
                            self.queue.put(self.CONTINUE_SPEAK_ENTRIES)
                            process.terminate()
                            break
                        
                        time.sleep(0.1)
                    
                    if self.thrdSpeakEntries.getContinue():
                        self.thrdSpeakEntries.unsetContinue()
                        break
                
                entry.spoken = True
                entry.save()
        finally:
            try:
                #self.queue.put(self.STOP_SPEAK_ENTRIES)
                process.terminate()
            except:
                logger.debug("Couldn't terminate process")
    
    def execSpeakEntries(self):
        if self.thrdSpeakEntries != None and self.thrdSpeakEntries.isAlive():
            logger.debug("Already speaking entries")
            return
        logger.debug("Speaking news entries")

        self.thrdSpeakEntries = ThreadedTask(target = self.speakEntries)
        self.thrdSpeakEntries.start()
        self.after(100, self.process_queue)
    
    def killSpeakEntries(self):
        if self.thrdSpeakEntries == None or not self.thrdSpeakEntries.isAlive():
            logger.debug("Not currently speaking")
            return
        logger.debug("Stopping the speak entries")
        self.thrdSpeakEntries.stop()
        self.thrdSpeakEntries.join()
        self.after(100, self.process_queue)
    
    def skipEntry(self):
        if self.thrdSpeakEntries == None or not self.thrdSpeakEntries.isAlive():
            logger.debug("Not currently speaking")
            return
        logger.debug("Stopping the speak entries")
        self.thrdSpeakEntries.setContinue()
        self.after(100, self.process_queue)

def _async_raise(tid, exctype):
    '''Raises an exception in the threads with id tid'''
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # """if it returns a number greater than one, you're in trouble, 
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
    else:
        logger.debug("Raised the excption %s in thread %d" % (exctype, tid))

class ThreadedTask(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(ThreadedTask, self).__init__(*args, **kwargs)
        self._stop = threading.Event()
        self._continue = threading.Event()
    
    def _get_my_tid(self):
        """determines this (self's) thread id"""
        if not self.isAlive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        raise AssertionError("could not determine the thread's id")

    def raise_exc(self, exctype):
        """raises the given exception type in the context of this thread"""
        _async_raise(self._get_my_tid(), exctype)

    def terminate(self):
        """raises SystemExit in the context of the given thread, which should 
        cause the thread to exit silently (unless caught)"""
        self.raise_exc(SystemExit)
    
    def stop(self):
        self._stop.set()
    
    def stopped(self):
        return self._stop.isSet()
    
    def setContinue(self):
        self._continue.set()
    
    def getContinue(self):
        return self._continue.isSet()
    
    def unsetContinue(self):
        self._continue.clear()
