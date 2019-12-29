import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"
enable_flair_posts = """
[Enabled Plugins]
word_notifier
"""

@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)

def test_notify(create_bot):
    wiki_trigger_words = """
    [Setup]
    word_list = ["12345", "abcdef", "aaa"]
    ignore_users = ["JohnDoe2"]
    """
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("word_notifier", wiki_trigger_words)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="title_test",
        body="blabla qweqw")
    test.advance_time_10m()

    submission = test.FakeSubmission(
        subreddit_name="some_other_sub",
        author_name="JohnDoe1",
        title="title_test",
        body="12345 oqiwjeoqiw aaa xxxabcdefxxx")
    test.advance_time_10m()

    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Check that modmail has been sent
    assert(len(sub.modmail) == 1)

    submission.add_comment("user1", "12345 1234")
    test.advance_time_10m()

    # Check that modmail has been sent
    assert(len(sub.modmail) == 2)