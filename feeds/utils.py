# Code adapted from https://github.com/Rotten194/summarize.py
import imp
import itertools
import nltk
from nltk.corpus import stopwords
import string

import bs4
import re
import requests

# Initialize the logging library
import logging
logger = logging.getLogger(__name__)

stop_words = stopwords.words('english')

LOWER_BOUND = .20 #The low end of shared words to consider
UPPER_BOUND = .90 #The high end, since anything above this is probably SEO garbage or a duplicate sentence


available_parsers = ["html.parser",]

try:
    imp.find_module("lxml")
    available_parsers.append("lxml")
except ImportError:
    pass
try:
    imp.find_module("html5lib")
    available_parsers.append("html5lib")
except ImportError:
    pass


def is_unimportant(word):
    """Decides if a word is ok to toss out for the sentence comparisons"""
    return word in ['.', '!', ',', ] or '\'' in word or word in stop_words

def only_important(sent):
    """Just a little wrapper to filter on is_unimportant"""
    return filter(lambda w: not is_unimportant(w), sent)

def compare_sents(sent1, sent2):
    """Compare two word-tokenized sentences for shared words"""
    if not len(sent1) or not len(sent2):
        return 0
    return len(set(only_important(sent1)) & set(only_important(sent2))) / ((len(sent1) + len(sent2)) / 2.0)

def compare_sents_bounded(sent1, sent2):
    """If the result of compare_sents is not between LOWER_BOUND and
    UPPER_BOUND, it returns 0 instead, so outliers don't mess with the sum"""
    cmpd = compare_sents(sent1, sent2)
    if cmpd <= LOWER_BOUND or cmpd >= UPPER_BOUND:
        return 0
    return cmpd

def compute_score(sent, sents):
    """Computes the average score of sent vs the other sentences (the result of
    sent vs itself isn't counted because it's 1, and that's above
    UPPER_BOUND)"""
    if not len(sent):
        return 0
    return sum( compare_sents_bounded(sent, sent1) for sent1 in sents ) / float(len(sents))

def summarize_block(block):
    """Return the sentence that best summarizes block"""
    sents = nltk.sent_tokenize(block)
    word_sents = map(nltk.word_tokenize, sents)
    d = dict( (compute_score(word_sent, word_sents), sent) for sent, word_sent in zip(sents, word_sents) )
    return d[max(d.keys())]

def find_likely_body(b):
    """Find the tag with the most directly-descended <p> tags"""
    return max(b.find_all(), key=lambda t: len(t.find_all('p', recursive=False)))

class Summary(object):
    def __init__(self, url, parser="html.parser"):
        self.url = url
        
        if parser not in available_parsers:
            logging.error("Available parsers are: %s" % (available_parsers,))
            raise ImportError
        
        try:
            self.soup = bs4.BeautifulSoup(requests.get(url).text, parser)
        except requests.exceptions.ConnectionError:
            print "Connection error getting url data"
            return None
        self.title = self.soup.title.string if self.soup.title else None
        self.article_html = find_likely_body(self.soup)
        parts = map(lambda p: re.sub('\s+', ' ', summarize_block(p.text)).strip(), self.article_html.find_all('p'))
        parts = sorted(set(parts), key=parts.index) #dedpulicate and preserve order
        self.parts = [ re.sub('\s+', ' ', summary.strip()) for summary in parts if filter(lambda c: c.lower() in string.letters, summary) ]
        self.content = ' '.join(self.parts)
    
    def __unicode__(self):
        return 'Summary of %s' % (self.url,)
