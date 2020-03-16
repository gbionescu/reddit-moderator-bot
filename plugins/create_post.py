import argparse
from modbot import hook
from modbot.log import botlog
from modbot.utils import parse_wiki_content, cron_next, utcnow, timestamp_string
from modbot.reddit_wrapper import post_submission_text, get_submission, get_comment, get_subreddit

plugin_documentation = r"""
This plugin allows mods to schedule posts at regular intervals.
Once a post is scheduled, a new wiki page will be updated automatically with the next post time.
You can find the wiki page at https://www.reddit.com/r/subreddit/wiki/schedule_posts_status

Before continuing, you should know that this wiki syntax is based on Pythons configparser: https://docs.python.org/3/library/configparser.html

To schedule a post, a section has to be specified. For example: [post_me_at_12AM]
Each section (or scheduled post) needs to have a few variables defined:
- title - title for the post
- interval - posting interval - use https://crontab.guru/ to check an interval

The 'interval' syntax has the following format:
* * * * * *
| | | | | |
| | | | | .. year (yyyy or * for any)
| | | | ...... day of week (1 - 7) (1 to 7 are Monday to Sunday)
| | | ........... month (1 - 12)
| | ................ day of month (1 - 31)
| ..................... hour (0 - 23)
.......................... min (0 - 59)

Each section has to have only ONE of these defined:
- body - post body
- wikibody - uses a reddit wiki page as the source for the body
- clonepost - uses a reddit post as the source for the body

The optional variables are:
- sticky - decide whether a post will be sticked (only the bottom post will be stickied)

The title or the post body can contain date-related variables:
- ${DAY} will be replaced by the day of the month (e.g 04, 13, 22)
- ${MONTH} will be replaced by the month number (e.g. 01, 11)
- ${YEAR} will be replaced by the year (e.g. 2011, 2022)

To better understand how a post is scheduled, take a look at the following examples:
[post_at_12AM]
title = test1 test2 ${DAY}.${MONTH}.${YEAR}
body = I will be posted at 12AM
    The body can also be multiline
    as long as I indent the lines further than
    the variable name
interval = 0 0 * * * *

[post_at_1AM]
title = test3 test4
wikibody = post1AM
interval = 0 1 * * * *

[post_at_2AM]
title = test5 test6
clonepost = https://redd.it/randompost
interval = 0 2 * * * *

In the example above, there are 3 scheduled posts:
1. post_at_12AM
This post is scheduled for 12AM as given in the interval syntax by "0 0 * * * *"
The body is given by 'body'

2. post_at_1AM
This post is scheduled for 1AM as given in the interval syntax by "0 1 * * * *"
The body is given by a wiki page that will be taken from https://www.reddit.com/r/subreddit/wiki/post1AM

3. post_at_2AM
This post is scheduled for 2AM as given in the interval syntax by "0 2 * * * *"
The body is given by copying a reddit post from https://redd.it/randompost
"""

MAX_TIME_OFFSET = 90

class SchedPost():
    def __init__(self, data, name):
        self.title = data.get("title", None)
        self.body = data.get("body", None)
        self.wikibody = data.get("wikibody", None)
        self.clonepost = data.get("clonepost", None)
        self.interval = data.get("interval", None)
        self.sticky = data.get("sticky", None)
        self.name = name

        self.valid = True

        self.cron_next = None
        try:
            self.cron_next = cron_next(self.interval)
        except:
            self.valid = False

        if not self.interval or \
            not self.title:
            self.valid = False

        if not self.body and \
            not self.wikibody and \
            not self.clonepost:
            self.valid = False


class Posts():
    def __init__(self):
        self.posts = []

    def add_post(self, post):
        if post.valid == False:
            return
        self.posts.append(post)

    def get_posts(self):
        for post in self.posts:
            yield post

wiki_config = {}

def update_posts_status(sub, cfg):
    wiki_page = ""
    for post in cfg.get_posts():
        wiki_page += "%s will be posted at %s\n" % (post.name, timestamp_string(post.cron_next))

    subreddit = get_subreddit(sub)
    subreddit.wiki("schedule_posts_status").edit(wiki_page)

def wiki_changed(sub, change):
    logger.debug("Wiki changed for create_post, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    # Read the setup section
    cfg = Posts()

    # Read each autoflair section
    for section in cont:
        if section == "DEFAULT":
            continue
        # Add it to config
        cfg.add_post(SchedPost(cont[section], section))

    # Save the config
    wiki_config[sub.display_name] = cfg
    logger.debug("Added config to wiki_config. Current list: %s" %
                 str(wiki_config.keys()))

    update_posts_status(sub.display_name, cfg)

# Register wiki page
wiki = hook.register_wiki_page(
    wiki_page="schedule_posts",
    description="Schedule submissions to be posted",
    documentation=plugin_documentation,
    wiki_change_notifier=wiki_changed)

logger = botlog("create_post")

def create_new_elem():
    new_elem = {}
    new_elem["shortlink"] = ""
    new_elem["integrated_comms"] = []
    new_elem["sticky"] = False
    new_elem["subreddit"] = ""
    new_elem["clone_source"] = ""
    new_elem["body"] = ""
    new_elem["wikibody"] = ""

    return new_elem

def post_submission(storage, subreddit, title, body, sticky):
    posted = post_submission_text(
        sub_name=subreddit,
        title=title,
        body=body,
        sticky=sticky)

    new_elem = create_new_elem()

    new_elem["shortlink"] = posted.shortlink
    new_elem["subreddit"] = subreddit
    if sticky:
        new_elem["sticky"] = True
    else:
        new_elem["sticky"] = False

    logger.debug("Created a new post at %s" % posted.shortlink)

    if "posts" not in storage:
        storage["posts"] = []

    storage["posts"].append(new_elem)

    return new_elem

def post_with_raw_body(storage, subreddit, title, body, sticky):
    posted = post_submission(storage, subreddit, title, body, sticky)

    posted["body"] = body
    storage.sync()
    return posted


def post_with_wiki_body(storage, subreddit, title, wiki_name, sticky):
    # Get the subreddit
    sub = get_subreddit(subreddit)

    # Get wiki body
    body = sub.wiki(wiki_name).content

    posted = post_submission(storage, subreddit, title, body, sticky)

    posted["wikibody"] = wiki_name
    storage.sync()
    return posted


def post_with_clone_body(storage, subreddit, title, clone_thread, sticky):
    # Get the subreddit
    sub = get_submission(clone_thread)

    posted = post_submission(storage, subreddit, title, sub.selftext, sticky)

    posted["clone_source"] = sub.shortlink
    storage.sync()
    return posted


@hook.command(permission=hook.permission.MOD)
def create_post(message, cmd_args, storage):
    """
    Create a bot post
    """
    parser = argparse.ArgumentParser(prog='create_post')
    parser.add_argument("--subreddit", help="subreddit to post in")
    parser.add_argument(
        "--sticky", help="sticky - specify to sticky", action='store_true')
    parser.add_argument("--title", help="post title",
                        type=str, action='store', nargs='+')
    parser.add_argument("--body", help="post body",
                        type=str, action='store', nargs='*')
    parser.add_argument("--wikibody", help="post body taken from a wiki")

    args = parser.parse_args(cmd_args)

    if not args.subreddit or \
            not args.title:
        message.author.send_pm("Invalid parameters", parser.print_help())

    if not args.body and not args.wikibody:
        message.author.send_pm(
            "Needs either --body or --wikibody", parser.print_help())

    title = args.title
    if type(args.title) == list:
        title = " ".join(args.title)

    # Check the body type and post it
    posted = None
    body = ""
    wiki_name = ""
    if args.body:
        body = args.body
        posted = post_with_wiki_body(storage, args.subreddit, title, wiki_name, args.sticky)

        if type(body) == list:
            body = " ".join(body)
    elif args.wikibody:
        # Get the subreddit
        sub = get_subreddit(args.subreddit)

        # Get the wiki name
        wiki_name = args.wikibody.replace("/", " ").strip().split(" ")[-1]

        # Get the wiki content
        body = sub.wiki(wiki_name).content
        posted = post_with_wiki_body(storage, args.subreddit, title, wiki_name, args.sticky)

    if not posted:
        logger.error("None post returned")
        return

    logger.debug("Created a new post at %s" % posted["shortlink"])
    message.author.send_pm("Create post result", "Done: %s" % posted["shortlink"])


@hook.command(permission=hook.permission.MOD)
def clone_post(message, cmd_args, storage):
    """
    Clone a post and keep its body in sync with the original
    """
    parser = argparse.ArgumentParser(prog='create_post')
    parser.add_argument("--subreddit", help="subreddit to post in")
    parser.add_argument(
        "--sticky", help="sticky - specify to sticky", action='store_true')
    parser.add_argument("--sub_link", help="post to clone")
    parser.add_argument("--title", help="post title",
                        type=str, action='store', nargs='*')

    args = parser.parse_args(cmd_args)

    if not args.subreddit or \
            not args.title or \
            not args.sub_link:
        message.author.send_pm("Invalid parameters", parser.print_help())

    title = args.title
    if type(args.title) == list:
        title = " ".join(args.title)

    # Post it
    posted = post_with_clone_body(storage, args.subreddit, title, args.sub_link, args.sticky)

    logger.debug("Created a new post at %s" % posted["shortlink"])
    message.author.send_pm("Create post result", "Done: %s" % posted["shortlink"])


@hook.command(permission=hook.permission.MOD)
def integrate_comment(message, cmd_args, storage):
    """
    Continuously integrate a comment in the body
    """
    parser = argparse.ArgumentParser(prog='integrate_comment')
    parser.add_argument("--sub_link", help="submission id")
    parser.add_argument("--comment_link", help="link to comment")
    args = parser.parse_args(cmd_args)

    # Check parameters
    if not args.sub_link or \
            not args.comment_link:
        message.author.send_pm("Invalid parameters", parser.print_help())

    if "posts" not in storage:
        storage["posts"] = []

    sub = get_submission(args.sub_link)

    # Get submission from storage
    target = None
    for elem in storage["posts"]:
        if elem["shortlink"] == sub.shortlink:
            target = elem
            break

    if not target:
        message.author.send_pm("No such post found", "No such post")

    # Get the comment id
    comm_id = None
    try:
        comm_id = args.comment_link.replace("/", " ").strip().split(" ")[-1]
    except:
        message.author.send_pm("Could not parse comment id", "")
        return

    # Check if it's in the list already
    if comm_id not in elem["integrated_comms"]:
        elem["integrated_comms"].append(comm_id)
        message.author.send_pm("Commend ID added to watch",
                               "Will watch %s in %s" % (comm_id, sub.shortlink))
    else:
        message.author.send_pm("Commend ID already added",
                               "Already watching %s in %s" % (comm_id, sub.shortlink))

    storage.sync()
    gather_body(sub, target)


@hook.command(permission=hook.permission.MOD)
def nointegrate_comment(message, cmd_args, storage):
    """
    Remove an integrated comment
    """
    parser = argparse.ArgumentParser(prog='nointegrate_comment')
    parser.add_argument("--sub_link", help="submission id")
    parser.add_argument("--comment_link", help="link to comment")
    args = parser.parse_args(cmd_args)

    # Check parameters
    if not args.sub_link or \
            not args.comment_link:
        message.author.send_pm("Invalid parameters", parser.print_help())

    if "posts" not in storage:
        storage["posts"] = []

    sub = get_submission(args.sub_link)

    # Get submission from storage
    target = None
    for elem in storage["posts"]:
        if elem["shortlink"] == sub.shortlink:
            target = elem
            break

    if not target:
        message.author.send_pm("No such post found", "No such post")

    # Get the comment id
    comm_id = None
    try:
        comm_id = args.comment_link.replace("/", " ").strip().split(" ")[-1]
    except:
        message.author.send_pm("Could not parse comment id", "")
        return

    # Check if it's in the list already
    if comm_id in elem["integrated_comms"]:
        elem["integrated_comms"].remove(comm_id)
        message.author.send_pm("Commend ID removed from watch",
                               "Will not watch %s in %s" % (comm_id, sub.shortlink))
    else:
        message.author.send_pm(
            "Commend ID not watched", "Not watching %s in %s" % (comm_id, sub.shortlink))

    storage.sync()
    gather_body(sub, target)


@hook.command(permission=hook.permission.MOD)
def resticky(message, cmd_args, storage):
    """
    Resticky a thread
    """
    parser = argparse.ArgumentParser(prog='resticky')
    parser.add_argument("--sub_link", help="submission id")
    args = parser.parse_args(cmd_args)

    # Check parameters
    if not args.sub_link:
        message.author.send_pm("Invalid parameters", parser.print_help())

    if "posts" not in storage:
        storage["posts"] = []

    sub = get_submission(args.sub_link)

    # Get submission from storage
    target = None
    for elem in storage["posts"]:
        if elem["shortlink"] == sub.shortlink:
            target = elem
            break

    if not target:
        message.author.send_pm("No such post found", "No such post")

    elem["sticky"] = True
    sub.make_sticky()
    storage.sync()


@hook.periodic(period=60 * 2)
def check_contents(storage):
    if "posts" not in storage:
        return

    for elem in storage["posts"]:
        # Skip unsticked submissions
        if elem["sticky"] == False:
            continue

        submission = get_submission(elem["shortlink"])
        if submission.stickied:
            # If still sticky, update it
            gather_body(submission, elem)
        else:
            # If unsticked, mark as unsticky
            elem["sticky"] = False

            # Sync changed elements
            storage.sync()


def gather_body(submission, stored):
    logger.debug("[%s] gathering body" % stored["shortlink"])

    all_body = ""
    # Check the body source
    # Order is important!
    if stored["clone_source"]:
        # Post was cloned from another post
        original_post = get_submission(stored["clone_source"])
        all_body = original_post.selftext
        logger.debug("[%s] it's a clone" % stored["shortlink"])
    elif stored["wikibody"]:
        # Get the subreddit
        sub = get_subreddit(stored["subreddit"])

        # Get the wiki content
        all_body = sub.wiki(stored["wikibody"]).content
    elif stored["body"]:
        # Plain post with a fixed body
        all_body = stored["body"]
        logger.debug("[%s] it's a self text" % stored["shortlink"])

    for comment_id in stored["integrated_comms"]:
        comm = get_comment(comment_id)
        all_body += "\n***\n"
        all_body += comm.body
        all_body += "\n\nContributor: /u/%s, [source](%s)" % (
            str(comm.author), comm.permalink)

    submission.edit(all_body)

@hook.periodic(period=30)
def scheduled_posts(storage):
    # For each subreddit
    for sub_name, cfg in wiki_config.items():
        # For each scheduled post

        something_changed = False
        for post in cfg.get_posts():
            # Check if we're within the posting timeframe
            timeframe = utcnow() - post.cron_next
            if timeframe > 0 and timeframe < MAX_TIME_OFFSET:

                something_changed = True

                if post.body:
                    post_with_raw_body(storage, sub_name, post.title, post.body, post.sticky)
                elif post.wikibody:
                    post_with_wiki_body(storage, sub_name, post.title, post.wikibody, post.sticky)
                elif post.clonepost:
                    post_with_clone_body(storage, sub_name, post.title, post.clonepost, post.sticky)

            post.cron_next = cron_next(post.interval)

        # If a post was posted then the scheduled time has changed
        # Update the status wiki
        if something_changed:
            update_posts_status(sub_name, cfg)
