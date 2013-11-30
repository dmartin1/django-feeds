from feeds.models import Category, Feed, Entry, EntryFieldChoice
from django.contrib import admin


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ('name',)}

class FeedAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'status', 'bozo', 'bozo_exception')
    list_filter = ('category',)
    
    fieldsets = (
        ('Basics', {
            'fields': ('name', 'category', 'feed_url', 'speech_fields', 'url', 'enabled')
        }),
        ('Feedparser Fields', {
            'classes': ('collapse',),
            'fields': ('last_checked', 'last_cached', 'last_modified', 'bozo', 'bozo_exception', 'encoding', 'etag', 'href', 'status', 'version')
        }),
    )

def mark_spoken(modeladmin, request, queryset):
    queryset.update(spoken=True)
mark_spoken.short_description = "Mark selected entries as spoken"

def mark_read(modeladmin, request, queryset):
    queryset.update(read=True)
mark_read.short_description = "Mark selected entries as read"

def summarize(modeladmin, request, queryset):
    for entry in queryset:
        entry.summarize()
summarize.short_description = "Summarize entries"

class EntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'feed', 'published', 'spoken', 'read', 'summarized')
    list_filter = ('spoken', 'read', 'summarized', 'feed')
    search_fields = ['comments', 'content', 'summary', 'title']
    
    actions = [mark_spoken, mark_read, summarize]

admin.site.register(Category, CategoryAdmin)
admin.site.register(Feed, FeedAdmin)
admin.site.register(Entry, EntryAdmin)
#admin.site.register(EntryFieldChoice)