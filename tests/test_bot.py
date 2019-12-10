import pytest
import modbot.input.test as test
from modbot.bot import bot

enable_flair_posts = """
[Enabled Plugins]
flair_posts
"""

wiki_flair_posts = """
[Setup]
message_intervals = 5, 10, 20
autoflair = 1

message = message ${MESSAGE_NO}/${MAX_MESSAGES}/${SUBMISSION_LINK}

[autoflair_test1]
title_contains = ["testa", "testb"]
flair_css_class = "testflair"
"""

def test_bot():

    test.set_moderated_subs(["testsub"])

    bot(bot_config_path="tests/test-bot.ini", backend="test")

    test.set_initial_sub(test.FakeSubmission(subreddit_name="testsub", author_name="JohnDoe1", title="title1"))

    for _ in range(30):
        test.advance_time_60s()

    # Create empty submissions
    test.FakeSubmission(subreddit_name="testsub", author_name="JohnDoe1", title="title2")
    test.FakeSubmission(subreddit_name="testsub", author_name="JohnDoe1", title="title3")
    test.FakeSubmission(subreddit_name="testsub", author_name="JohnDoe1", title="title4")
    test.FakeSubmission(subreddit_name="testsub", author_name="JohnDoe1", title="title5")
    # Update last seen submission
    test.new_all_sub(test.FakeSubmission(subreddit_name="testsub", author_name="JohnDoe1", title="title5"))

    sub = test.get_subreddit("testsub")

    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("flair_posts", wiki_flair_posts)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    # Create a new sub
    test.new_all_sub(test.FakeSubmission(subreddit_name="testsub", author_name="JohnDoe1", title="title6"))

    for _ in range(30):
        test.advance_time_60s()