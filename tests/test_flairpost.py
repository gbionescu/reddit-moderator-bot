import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"
enable_flair_posts = """
[Enabled Plugins]
flair_posts
"""

@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)

def test_flair_warning(create_bot):
    wiki_flair_posts = """
    [Setup]
    message_intervals = 5, 7, 9, 10, 15, 20, 25
    autoflair = 1

    message = message ${MESSAGE_NO}/${MAX_MESSAGES}/${SUBMISSION_LINK}

    [autoflair_test1]
    title_contains = ["testa", "testb"]
    flair_css_class = "testflair"
    """
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("flair_posts", wiki_flair_posts)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    # Create a new submissinon that we will be testing against
    test_submission = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1", title="title_test")
    test.new_all_sub(test_submission)

    # Give the bot time to send all messages
    test.advance_time_30m()

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

def test_auto_flair(create_bot):
    wiki_flair_posts = """
    [Setup]
    autoflair = 1

    [autoflair_test1]
    title_contains = ["test1", "test2"]
    flair_css_class = "testflair1"

    [autoflair_test2]
    title_contains = ["test3", "test4"]
    flair_css_class = "testflair2"

    [autoflair_test3]
    body_contains = ["test5", "test6"]
    flair_css_class = "testflair3"

    [autoflair_test4]
    domain = ["redditbot.com", "pula.ro"]
    flair_css_class = "testflair4"

    [autoflair_test5]
    title_contains = ["prio1", "prio2"]
    flair_css_class = "testflair5"
    priority = 50

    [autoflair_test6]
    title_contains = ["prio1", "prio2"]
    flair_css_class = "testflair6"
    priority = 40
    """

    sub = test.get_subreddit(TEST_SUBREDDIT)
    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("flair_posts", wiki_flair_posts)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    subreddit = test.get_subreddit(TEST_SUBREDDIT)
    subreddit.set_flairs([
        "testflair1",
        "testflair2",
        "testflair3",
        "testflair4",
        "testflair5",
        "testflair6"])

    ### Test titles
    test_submission1 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="blabla test1 blabla")

    test_submission2 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe2",
        title="blabla test4 blabla")
    test.new_all_sub(test_submission2)

    # Give the bot time to send all messages
    for _ in range(30):
        test.advance_time_60s()

    assert(test_submission1.flairs.set_flair_id == "testflair1")
    assert(test_submission2.flairs.set_flair_id == "testflair2")

    ### Test body
    test_submission3 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="blabla 1234 blabla",
        body="qoweiqoiejqoiwjq test5 pqioejoqij")

    test.new_all_sub(test_submission3)

    # Give the bot time to send all messages
    for _ in range(30):
        test.advance_time_60s()

    assert(test_submission3.flairs.set_flair_id == "testflair3")

    ### Test domain
    test_submission4 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="blabla 1234 blabla",
        link="https://www.redditbot.com/12345.123")

    test.new_all_sub(test_submission4)

    # Give the bot time to send all messages
    test.advance_time_30m()

    assert(test_submission4.flairs.set_flair_id == "testflair4")

    ### Test priority
    test_submission5 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="blabla prio2 blabla")

    test.new_all_sub(test_submission5)

    # Give the bot time to send all messages
    test.advance_time_30m()

    assert(test_submission5.flairs.set_flair_id == "testflair6")

def test_corner_cases(create_bot):
    wiki_flair_posts = """
    [Setup]
    message_intervals = 2, 30

    message = message ${MESSAGE_NO}/${MAX_MESSAGES}/${SUBMISSION_LINK}
    """
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("flair_posts", wiki_flair_posts)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_10m()

    # Create new submissions
    test_submission1 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe123",
        title="random title")

    test_submission2 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe123",
        title="random title")

    test_submission3 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe123",
        title="random title")

    test.new_all_sub(test_submission3)

    # Advance a few minutes so that one message is sent
    test.advance_time_10m()

    # Remove it by a mod
    test_submission1.delete_by_mod()

    # Remove it by the author
    test_submission2.delete_by_author()

    # Add flair by user
    test_submission3.set_link_flair_text("asdfg")

    # Give the bot time to remove the posts from queues
    test.advance_time_30m()
    test.advance_time_30m()

    user = test.get_user("JohnDoe123")

    # Check that 2 messages have been sent
    assert(len(user.inbox) == 3)

    # Try to exceed minimum trigger time
    test_submission4 = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="granular",
        title="random title")
    test.advance_time_10m()
    test.new_all_sub(test_submission4)

    assert(len(test.get_user("granular").inbox) == 0)

def test_invalid_cfg(create_bot):
    wiki_flair_posts = """
    [Seup]
    message_intervals = 2, 30

    message = message ${MESSAGE_NO}/${MAX_MESSAGES}/${SUBMISSION_LINK}
    """
    test.create_bot(TEST_SUBREDDIT)
    sub = test.get_subreddit(TEST_SUBREDDIT)
    # Update flair posts control panel
    sub.edit_wiki("control_panel", enable_flair_posts)
    sub.edit_wiki("flair_posts", wiki_flair_posts, author="wikieditboy")

    test.advance_time_30m()

    assert(len(test.get_user("wikieditboy").inbox) == 1)