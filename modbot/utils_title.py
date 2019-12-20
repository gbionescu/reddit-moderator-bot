#-*-coding:utf8;-*-
#qpy:3
#qpy:console
import unicodedata
import string

'''
Extract the title from a web page using
the standard lib.
'''

from html.parser import HTMLParser
from urllib.request import urlopen
import urllib

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

def get_title(url):
    return Parser(url).title

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def clean_title(title, min_word_len):
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