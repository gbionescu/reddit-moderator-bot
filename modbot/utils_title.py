#-*-coding:utf8;-*-
#qpy:3
#qpy:console
import unicodedata
import string
import urllib
import collections
from html.parser import HTMLParser
from urllib.request import urlopen

class Parser(HTMLParser):
    def __init__(self, url):
        self.title = None
        self.rec = False
        HTMLParser.__init__(self)
        try:
            self.feed(to_ascii(urlopen(url).read()))
        except urllib.error.HTTPError:
            return
        except urllib.error.URLError:
            return
        except ValueError:
            return

        self.rec = False
        self.error = error_callback

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.rec = True

    def handle_data(self, data):
        if self.rec:
            self.title = data

    def handle_endtag(self, tag):
        if tag == 'title':
            self.rec = False

# Keep an association of URL to titles so that we don't make multiple requests
# Using a simple deque - a dict-queue would be faster
url_title_cache = collections.deque(maxlen=20)

def error_callback(*_, **__):
    pass

def is_string(data):
    return isinstance(data, str)

def is_bytes(data):
    return isinstance(data, bytes)

def to_ascii(data):
    if is_string(data):
        data = data.encode('utf-8', errors='ignore')
    elif is_bytes(data):
        data = data.decode('utf-8', errors='ignore')
    else:
        data = str(data).encode('ascii', errors='ignore')
    return data

def get_title(url):
    for stored_url, stored_title in url_title_cache:
        if url == stored_url:
            return stored_title

    # Fetch the title
    try:
        title = Parser(url).title
    except:
        title = ""
    url_title_cache.append((url, title))

    return title

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def clean_title(title, min_word_len=1):
    if not title:
        return []

    # Remove punctuation, lower, remove accents and split
    split = remove_accents(
            title.translate(str.maketrans(dict.fromkeys(string.punctuation))).lower()
        ).split()

    # Remove words shorter than min_word_len
    no_shortw = []
    for word in split:
        if len(word) <= min_word_len:
            continue

        no_shortw.append(word)

    return no_shortw
