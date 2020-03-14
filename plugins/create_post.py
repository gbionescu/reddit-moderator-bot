import argparse
from modbot import hook
from modbot.log import botlog
from modbot.reddit_wrapper import post_submission_text, get_submission, get_comment, get_subreddit

logger = botlog("create_post")

def create_new_elem():
    new_elem = {}
    new_elem["shortlink"] = ""
    new_elem["integrated_comms"] = []
    new_elem["sticky"] = False
    new_elem["subreddit"] = ""
    new_elem["clone_source"] = ""
    new_elem["body"] = ""

    return new_elem

@hook.command(permission=hook.permission.MOD)
def create_post(message, cmd_args, storage):
    """
    Create a bot post
    """
    parser = argparse.ArgumentParser(prog='create_post')
    parser.add_argument("--subreddit", help="subreddit to post in")
    parser.add_argument("--sticky", help="sticky - specify to sticky", action='store_true')
    parser.add_argument("--title", help="post title")
    parser.add_argument("--body", help="post body")

    args = parser.parse_args(cmd_args)

    if not args.subreddit or \
        not args.title or \
        not args.body:
        message.author.send_pm("Invalid parameters", parser.print_help())

    posted = post_submission_text(
        sub_name = args.subreddit,
        title=args.title,
        body=args.body,
        sticky=args.sticky)

    message.author.send_pm("Create post result", "Done: %s" % posted.shortlink)

    if "posts" not in storage:
        storage["posts"] = []

    new_elem = create_new_elem()
    new_elem["shortlink"] = posted.shortlink
    if args.sticky:
        new_elem["sticky"] = True
    else:
        new_elem["sticky"] = False
    new_elem["subreddit"] = args.subreddit
    new_elem["body"] = args.body

    logger.debug("Created a new post at %s" % posted.shortlink)

    storage["posts"].append(new_elem)
    storage.sync()

@hook.command(permission=hook.permission.MOD)
def clone_post(message, cmd_args, storage):
    """
    Clone a post and keep its body in sync with the original
    """
    parser = argparse.ArgumentParser(prog='create_post')
    parser.add_argument("--subreddit", help="subreddit to post in")
    parser.add_argument("--sticky", help="sticky - specify to sticky", action='store_true')
    parser.add_argument("--sub_link", help="post to clone")
    parser.add_argument("--title", help="post title")

    args = parser.parse_args(cmd_args)

    if not args.subreddit or \
        not args.title or \
        not args.sub_link:
        message.author.send_pm("Invalid parameters", parser.print_help())

    original_post = get_submission(args.sub_link)

    posted = post_submission_text(
        sub_name = args.subreddit,
        title=args.title,
        body=original_post.selftext,
        sticky=args.sticky)

    if "posts" not in storage:
        storage["posts"] = []

    new_elem = create_new_elem()
    new_elem["shortlink"] = posted.shortlink
    if args.sticky:
        new_elem["sticky"] = True
    else:
        new_elem["sticky"] = False
    new_elem["subreddit"] = args.subreddit
    new_elem["clone_source"] = original_post.shortlink

    logger.debug("Created a new post at %s" % posted.shortlink)

    storage["posts"].append(new_elem)
    storage.sync()

    message.author.send_pm("Create post result", "Done: %s" % posted.shortlink)


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
        message.author.send_pm("Commend ID added to watch", "Will watch %s in %s" % (comm_id, sub.shortlink))
    else:
        message.author.send_pm("Commend ID already added", "Already watching %s in %s" % (comm_id, sub.shortlink))

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
        message.author.send_pm("Commend ID removed from watch", "Will not watch %s in %s" % (comm_id, sub.shortlink))
    else:
        message.author.send_pm("Commend ID not watched", "Not watching %s in %s" % (comm_id, sub.shortlink))

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
            # If unsticked, mark as unsticky and send a notification to modmail
            elem["sticky"] = False

            # Sync changed elements
            storage.sync()

            get_subreddit(elem["subreddit"]).send_modmail(
                "A post has been unsticked",
                "%s has been unsticked and no longer updated. "
                "Send me a reply containing \"/resticky %s\"" % (submission.shortlink, submission.shortlink))

def gather_body(submission, stored):
    logger.debug("[%s] gathering body" % stored["shortlink"])

    all_body = ""
    if not stored["clone_source"]:
        all_body = stored["body"]
        logger.debug("[%s] it's a self text" % stored["shortlink"])
    else:
        original_post = get_submission(stored["clone_source"])
        all_body = original_post.selftext
        logger.debug("[%s] it's a clone" % stored["shortlink"])

    for comment_id in stored["integrated_comms"]:
        comm = get_comment(comment_id)
        all_body += "\n***\n"
        all_body += comm.body
        all_body += "\nContributor: /u/%s, [source](%s)" % (str(comm.author), comm.permalink)

    submission.edit(all_body)