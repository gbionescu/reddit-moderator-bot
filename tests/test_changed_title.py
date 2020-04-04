import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"
enable_flair_posts = """
[Enabled Plugins]
changed_title
"""


@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)


def test_changed_title(create_bot):
    wiki_flair_posts = """
    [Setup]
    minimum_overlap_percent = 60
    domains = ["google.com", "blabla.co.uk"]
    """
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update control panel and plugin wiki
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("changed_title", wiki_flair_posts)

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    # Create fake articles
    test.FakeURL("https://google.com/myarticle1",
                 "I don't like mosquitoes because they suck blood")
    test.FakeURL("https://google.com/myarticle2",
                 "qwerty asdfg zxcvb poiuy lkjhg mnbvc")

    # Test it
    test_submission1 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="AAAA BBBB CCCC DDDD EEEE FFFF", url="https://google.com/myarticle1")
    test_submission2 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="qwerty asdfg zxcvb poiuy lkjhg mnbvc", url="https://google.com/myarticle2")
    test.advance_time_10m()

    assert(len(test_submission1.reports) == 1)
    assert(len(test_submission2.reports) == 0)


def test_invalid_cfg(create_bot):
    wiki_flair_posts = """
    [Seup]

    """
    test.create_bot(TEST_SUBREDDIT)
    sub = test.get_subreddit(TEST_SUBREDDIT)
    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("changed_title", wiki_flair_posts, author="wikieditboy")

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    test.advance_time_30m()

    assert(len(test.get_user("wikieditboy").inbox) == 1)
