import re
import requests
import os
import random
import string
from modbot.utils import utcnow

# Create storage directory
STORE_DIR = "temp_files/"
os.makedirs(STORE_DIR, exist_ok=True)

def gen_fname(sub_name, link):
    """
    Generate filename based on subreddit name and link
    """
    # Replace non alphabetical
    regex = re.compile('[^a-zA-Z]')
    link = regex.sub('', link)

    return STORE_DIR + sub_name + "_" + link + ".jpg"

def proc_imgur_url(starturl):
    """
    Process an imgur link
    """

    # If imgur is not in the link, skip it
    if "imgur.com" not in starturl:
        return starturl

    finishedurl = []
    regex = r"href\=\"https://i\.imgur\.com\/([\d\w]*)(\.jpg|\.png|\.gif|\.mp4|\.gifv)"
    try:
        imgurHTML = requests.get(starturl)
    except:
        raise Exception('Something failed')

    # Try finding all the embedded imgur links
    imgurhash = re.findall(regex, imgurHTML.text)

    # If no embedded links have been found, return the original url
    if len(imgurhash) == 0:
        return starturl

    finishedurl.append('https://i.imgur.com/{0}{1}'.format(imgurhash[0][0], imgurhash[0][1]))
    return finishedurl

def get_picture(url, fname, timeout_sec=20, max_size=1024*1024*20):
    if "imgur.com" in url:
        url = proc_imgur_url(url)

    req = requests.get(url, stream=True)
    req.raise_for_status()

    start = utcnow()
    content = bytes()
    size = 0

    # Get a chunk
    for chunk in req.iter_content(1024):
        # If download time exceeds the given timeout, exit
        if utcnow() - start > timeout_sec:
            print("Image %s took too long to download" % url)
            return None

        content += chunk
        size += len(chunk)

        # If the size eceeds the given maximum size, exit
        if size > max_size:
            print("Image %s is too large" % url)
            return None

    # Save the file
    save_data = open(fname, "wb")
    save_data.write(content)

    return fname