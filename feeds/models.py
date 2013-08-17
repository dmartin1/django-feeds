from datetime import datetime
from dateutil.parser import parse as dateutil_parser
from subprocess import call
from sys import platform as _platform
from time import mktime

from django.conf import settings
from django.db import models
from django.utils.timezone import get_current_timezone
from django.template.defaultfilters import striptags
from feeds.utils import Summary

import feedparser

# Initialize the logging library
import logging
logger = logging.getLogger(__name__)


SPEECH_FIELD_CHOICES = (
    ('feed', 'feed__name'),
    ('title', 'title'),
    ('content', 'content'),
    ('summary', 'summary'),
)

class Category(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True, max_length=64)
    
    class Meta:
        ordering            = ('name',)
        verbose_name        = 'category'
        verbose_name_plural = 'categories'
    
    def __unicode__(self):
        return self.name

class EntryFieldChoice(models.Model):
    name = models.CharField(max_length=50)
    
    def __unicode__(self):
        return self.name


class FeedManager(models.Manager):
    def unread(self):
        return self.get_query_set().filter(posts__read=False).distinct()

class Feed(models.Model):
    name            = models.CharField(max_length=255)
    category        = models.ForeignKey(Category)
    feed_url        = models.URLField(unique=True, help_text="URL of RSS/Atom feed")
    url             = models.URLField(blank=True, help_text="URL of website")
    enabled         = models.BooleanField(default=True, help_text="Poll this feed for new posts.")
    
    last_checked    = models.DateTimeField(blank=True, null=True, help_text="Date feedreader last checked this feed.")
    last_cached     = models.DateTimeField(blank=True, null=True, help_text="Date feedreader last cached posts from this feed.")
    last_modified   = models.DateTimeField(blank=True, null=True, help_text="The last-modified date of the feed, as specified in the HTTP headers.")

    bozo            = models.BooleanField(help_text="Set to True if the feed is not well-formed XML, and False otherwise.")
    bozo_exception  = models.CharField(max_length=255, blank=True, help_text="The exception raised when attempting to parse a non-well-formed feed.")
    encoding        = models.CharField(max_length=50, blank=True, help_text="The character encoding that was used to parse the feed.")
    etag            = models.CharField(max_length=255, blank=True, null=True, help_text="ETags and Last-Modified headers are two ways that feed publishers can save bandwidth")
    href            = models.URLField(blank=True, help_text="The final URL of the feed that was parsed.")
    status          = models.IntegerField(default=0, help_text="The most recent HTTP status code that was returned by the web server when the feed was fetched.")
    version         = models.CharField(max_length=50, blank=True, help_text="The format and version of the feed.")
    
    speech_fields   = models.ManyToManyField(EntryFieldChoice, help_text="Fields of Entry object that will be spoken.")
    
    objects = FeedManager()
    
    class Meta:
        verbose_name        = "feed"
        verbose_name_plural = "feeds"
        ordering            = ('name',)
    
    def __unicode__(self):
        return self.name
    
    def update(self):
        ## Check that the feed is enabled
        if self.enabled == False:
            logger.error("Feed not enabled: %s" % (self.name,))
            return
        
        ## Parse the feed
        if self.etag:
            logger.debug('Scraping %s using etag' % (self.name,))
            response = feedparser.parse(self.feed_url, etag=self.etag)
        elif self.last_modified:
            logger.debug('Scraping %s using last_modified' % (self.name,))
            response = feedparser.parse(self.feed_url, modified=self.last_modified)
        else:
            logger.debug('Scraping %s (full parse)' % (self.name,))
            response = feedparser.parse(self.feed_url)
        
        ## Update timestamps
        self.last_checked   = datetime.now().replace(tzinfo=get_current_timezone())
        if response.has_key('updated'):
            self.last_modified  = dateutil_parser(response.get('updated'))
        
        ## Update feed response fields
        self.bozo           = response.get('bozo', False)
        self.bozo_exception = response.get('bozo_exception', '')
        self.encoding       = response.get('encoding', '')
        self.etag           = response.get('etag', '')
        if response.has_key('href'):
            self.href       = response.get('href')
        self.status         = response.get('status', 0)
        self.version        = response.get('version', '')
        self.save()
        
        ## Status Checks
        if self.status == 301:
            # The feed was permanently redirected to a new URL.
            # Updating feed_url to request the new URL from now on.
            logger.info("Status 301 - Feed permanantly redirected: %s" % (self.name,))
            logger.info("%s -> %s" % (self.feed_url, response.get('href')))
            self.feed_url = response.get('href')
            self.save()
        elif self.status == 410:
            # The feed is gone.
            # Disabling the feed.
            logger.error("Status 410 - Feed no longer exists: %s" % (self.name,))
            self.enabled = False
            self.save()
            return
        elif self.status == 304:
            # The feed has not changed since the last time it was requested.
            # Stop processing.
            logger.debug("Status 304 - Feed has not changed: %s" % (self.name,))
            return
        elif self.status == 404:
            # The feed_url is incorrect or inaccessible.
            logger.error("Status 404 - Feed inaccessible: %s" % (self.name,))
            return
        else:
            pass
        
        ## Process entries list
        self.last_cached = datetime.now().replace(tzinfo=get_current_timezone())
        self.save()
        
        for entry in response.get('entries', []):
            if not entry.has_key('id'):
                entry['id'] = entry.get('link')
            
            obj, created = Entry.objects.get_or_create(uid = entry['id'], defaults={
                'author'    : entry.get('author', None),
                'comments'  : entry.get('comments', None),
                'content'   : striptags(entry.get('content', [{'value':''}])[0]['value']),
                'license'   : entry.get('license', None),
                'link'      : entry.get('link'),
                'published' : dateutil_parser(entry.get('published')),
                'publisher' : entry.get('publisher', None),
                'summary'   : striptags(entry.get('summary')),
                'title'     : entry.get('title'),
                
                'feed'      : self,
            })
            
            # Additional Processing
            if entry.has_key('created'):
                obj.created = dateutil_parser(entry.get('created'))
            
            if entry.has_key('expired'):
                obj.expired = dateutil_parser(entry.get('expired'))
            
            if entry.has_key('updated'):
                obj.expired = dateutil_parser(entry.get('updated'))
            
            obj.save()


class Entry(models.Model):
    feed                = models.ForeignKey('Feed')
    date_cached         = models.DateTimeField(auto_now_add=True)
    read                = models.BooleanField(default=False)
    spoken              = models.BooleanField(default=False, help_text="This entry has been read aloud.")
    summarized          = models.BooleanField(default=False, help_text="This entry's content field has been updated with the summarizer.")
    
    # Feedparser fields
    author              = models.CharField(blank=True, null=True, max_length=255, help_text="The author of this entry.")
    # author_detail       = # A dictionary with details about the author of this entry.
    comments            = models.URLField(blank=True, null=True, help_text="A URL of the HTML comment submission page associated with this entry.")
    content             = models.TextField(blank=True)# A list of dictionaries with details about the full content of the entry.
    # contributors        = # A list of contributors (secondary authors) to this entry.
    created             = models.DateTimeField(blank=True, null=True, help_text="The date this entry was first created (drafted).")
    # created_parsed      = # The date this entry was first created (drafted), as a standard Python 9-tuple.
    # enclosures          = # A list of links to external files associated with this entry.
    expired             = models.DateTimeField(blank=True, null=True, help_text="The date this entry is set to expire.")
    # expired_parsed      = # The date this entry is set to expire, as a standard Python 9-tuple.
    uid                 = models.CharField(max_length=255, unique=True, help_text="A globally unique identifier for this entry.")
    license             = models.URLField(blank=True, null=True, help_text="A URL of the license under which this entry is distributed.")
    link                = models.URLField(help_text="The primary link of this entry. Most feeds use this as the permanent link to the entry in the site's archives.")
    # links               = # A list of dictionaries with details on the links associated with the feed. Each link has a rel (relationship), type (content type), and href (the URL that the link points to). Some links may also have a title.
    published           = models.DateTimeField(help_text="The date this entry was first published.")
    # published_parsed    = # The date this entry was first published, as a standard Python 9-tuple.
    publisher           = models.CharField(max_length=255, blank=True, null=True, help_text="The publisher of the entry.")
    # publisher_detail    = # A dictionary with details about the entry publisher.
    # source              = # A dictionary with details about the source of the entry.
    summary             = models.TextField(help_text="A summary of the entry.  If this contains HTML or XHTML, it is sanitized by default.")
    # summary_detail      = # A dictionary with details about the entry summary.
    # tags                = # A list of dictionaries that contain details of the categories for the entry.
    title               = models.CharField(max_length=255, help_text="The title of the entry.  If this contains HTML or XHTML, it is sanitized by default.")
    # title_detail        = # A dictionary with details about the entry title.
    updated             = models.DateTimeField(blank=True, null=True, help_text="The date this entry was last updated.")
    # updated_parsed      = # The date this entry was last updated, as a standard Python 9-tuple.
    # vcard               = # An RFC 2426-compliant vCard derived from hCard information found in this entry's HTML content.
    # xfn                 = # A list of XFN relationships found in this entry's HTML content.
    
    class Meta:
        ordering            = ('-published',)
        verbose_name        = "entry"
        verbose_name_plural = "entries"
    
    def __unicode__(self):
        return self.title
    
    def speak_aloud(self, destination="Built-in Output"):
        if _platform == "darwin": # OS X uses the built-in 'say' command
            field_names = self.feed.speech_fields.values_list('name', flat=True)
            for field_name in field_names:
                logger.debug("Speaking %s field" % (field_name, ))
                call(["say", "-a", '%s' % (destination,), getattr(self, field_name)])
            self.spoken = True
            self.save()
        else:
            logger.error("%s is currently an unhandled operating system." % (_platform, ))
    
    def summarize(self, parser="html.parser"):
        logger.debug("Summarizing %s" % (self.title,))
        summary = Summary(self.link, parser)
        
        proposed_content = ''
        for part in summary.parts:
            if not getattr(settings, 'SUMMARIZE_WORD_COUNT_LIMIT', None) or len(proposed_content.split(' ')) < settings.SUMMARIZE_WORD_COUNT_LIMIT:
                proposed_content = proposed_content + ' ' + part
        
        self.content    = proposed_content
        self.summarized = True
        self.save()