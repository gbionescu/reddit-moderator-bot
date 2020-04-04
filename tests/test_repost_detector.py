import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"
enable_flair_posts = """
[Enabled Plugins]
repost_detector
"""


@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)


def test_repost_detector(create_bot):
    wiki_flair_posts = """
    [Setup]
    minimum_word_length = 3
    minimum_nb_words = 5
    min_overlap_percent = 50
    ignore_users = ["AutoModerator"]
    """
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update control panel and plugin wiki
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("repost_detector", wiki_flair_posts)

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    # Create a new submissinon that we will be testing against
    test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                        title="AAAA BBBB CCCC DDDD EEEE FFFF")

    test.advance_time_30m()

    # Create another submission
    test_submission2 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="AAAA BBBB CCCC DDDD EEEE GGGG")
    test.advance_time_10m()

    assert(len(test_submission2.reports) == 1)

    test.advance_time_30m()

    # Test short word elimination
    test_submission3 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="AAAA BBBB CCCC DDDD")

    assert(len(test_submission3.reports) == 0)

    # Jump in time one month
    test.advance_time(2592000)
    test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                        title="AAAB BBBC CCCD DDDE EEEG GGGF")
    # Give the chance to remove a post from storage due to being too old
    test.advance_time_30m()

    # Test user ignore
    test_submission4 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="automoderator",
                                           title="AAAA BBBB CCCC DDDD EEEE GGGG")
    test.advance_time_10m()

    assert(len(test_submission4.reports) == 0)


def test_invalid_cfg(create_bot):
    wiki_flair_posts = """
    [Seup]

    """
    test.create_bot(TEST_SUBREDDIT)
    sub = test.get_subreddit(TEST_SUBREDDIT)
    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("repost_detector", wiki_flair_posts,
                  author="wikieditboy_repost")

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    test.advance_time_30m()

    assert(len(test.get_user("wikieditboy_repost").inbox) == 1)
