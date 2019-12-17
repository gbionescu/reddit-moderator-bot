import pytest
import modbot.input.test as test
from modbot.bot import bot

TEST_SUBREDDIT = "testsub123"
enable_flair_posts = """
[Enabled Plugins]
flair_posts
"""

def do_initial_setup():
    """
    Bring up bot logic
    """
    test.set_moderated_subs([TEST_SUBREDDIT])
    bot(bot_config_path="tests/test-bot.ini", backend="test")

    test.set_initial_sub(test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title1"))

    # Start up and wait for a while
    for _ in range(10):
        test.advance_time_60s()

    # Create empty submissions
    test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title2")
    test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title3")

    # Update last seen submission
    test.new_all_sub(test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title4"))

    test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title5")
    test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title6")

    # Wait again for things to expire
    for _ in range(10):
        test.advance_time_60s()

def test_flair_warning():
    enable_flair_posts = """
    [Enabled Plugins]
    flair_posts
    """

    wiki_flair_posts = """
    [Setup]
    message_intervals = 5, 7, 9, 10, 15, 20, 25
    autoflair = 1

    message = message ${MESSAGE_NO}/${MAX_MESSAGES}/${SUBMISSION_LINK}

    [autoflair_test1]
    title_contains = ["testa", "testb"]
    flair_css_class = "testflair"
    """

    do_initial_setup()

    sub = test.get_subreddit(TEST_SUBREDDIT)
    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("flair_posts", wiki_flair_posts)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    # Create a new sub that we will be testing against
    test_submission = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title_test")
    test.new_all_sub(test_submission)

    # Give the bot time to send all messages
    for _ in range(30):
        test.advance_time_60s()

    user = test.get_user("JohnDoe1")

    # Check that 7 messages have been sent
    assert(len(user.inbox) == 7)

    # Check each inbox message
    msg_no = 1
    while len(user.inbox) != 0:
        _, text = user.inbox[0]
        assert("message %d/7/%s" % (msg_no, test_submission.shortlink) in text)

        msg_no += 1
        user.inbox = user.inbox[1:]

def test_autoflair():
    wiki_flair_posts = """
    [Setup]
    autoflair = 1

    [autoflair_test1]
    title_contains = ["test1", "test2"]
    flair_css_class = "testflair1"

    [autoflair_test2]
    title_contains = ["test3", "test4"]
    flair_css_class = "testflair2"
    """

    do_initial_setup()

    sub = test.get_subreddit(TEST_SUBREDDIT)
    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("flair_posts", wiki_flair_posts)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    # Create a new sub that we will be testing against
    test_submission = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="blabla test1 blabla")
    test.new_all_sub(test_submission)

    # Give the bot time to send all messages
    for _ in range(30):
        test.advance_time_60s()

    user = test.get_user("JohnDoe1")
