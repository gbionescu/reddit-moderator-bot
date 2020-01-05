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

def test_usernotes(create_bot):
    sub = test.get_subreddit(TEST_SUBREDDIT)

    unotes = sub.get_wiki("usernotes")
    unotes.set_content(open("tests/test_usernotes.json", "r").read(), "me")

    submission = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="title_test",
        body="12345 oqiwjeoqiw aaa xxxabcdefxxx")
    test.advance_time_10m()

    # Add a mod report
    submission.report("test1", "mod1")
    submission.report("test2", "invalid_mod")
    submission.report("test3")
    test.advance_time_10m()

    mod1 = test.get_user("mod1")

    assert(len(test.get_user("bot_owner").inbox) == 2)
    assert(len(mod1.inbox) == 0)

    submission.report("/get_notes", "invalid_mod")
    assert(len(test.get_user("bot_owner").inbox) == 3)

    submission.report("/get_notes", "mod1")
    assert(len(mod1.inbox) == 1)
    assert("Usernotes not found" in mod1.inbox[0])
    mod1.inbox = []

    submission2 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="RoCirclejerk",
        title="title_test",
        body="12345 oqiwjeoqiw aaa xxxabcdefxxx")
    test.advance_time_10m()

    submission2.report("/get_notes", "mod1")
    assert(len(mod1.inbox) == 1)
    assert("test1" in mod1.inbox[0][1])