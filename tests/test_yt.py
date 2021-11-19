import pytest
import modbot.input.test as test
import modbot.ytaccess as yt

TEST_SUBREDDIT = "testsub123"
yt_plugin = """
[Enabled Plugins]
youtube
"""

link_to_chanid = {
    "1": "101",
    "2": "102",
    "3": "103",
}

# Use a custom fetcher for testing
def fake_chan_fetcher(link):
    return link_to_chanid[link]

yt.get_channel_id = fake_chan_fetcher


@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)


def test_yt_post(create_bot):
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update control panel and plugin wiki
    sub.edit_wiki("control_panel", yt_plugin)
    sub.edit_wiki("youtube", r"""
    [ch1]
    id = 101
    message = got a post by some channel ${AUTHOR} ${KIND}

    [ch2]
    id = 102
    message = got a post by some channel ${AUTHOR} ${KIND}
    report = blah

    [ch3]
    id = 103
    message = got a post by some channel ${AUTHOR} ${KIND}
    delete = True
    """)

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_10m()

    ###
    # Test1
    ###
    test_submission1 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="asdfg", url="https://youtube.com/watch?v=1")
    test.advance_time_30s()

    # Check conditions are successful for t1
    assert(len(sub.modmail) == 1)
    assert(test_submission1.deleted == False)
    assert(len(test_submission1.reports) == 0)

    ###
    # Test2
    ###
    test_submission2 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="asdfg", url="https://youtube.com/watch?v=2")
    test.advance_time_30s()
    # Check conditions are successful for t2
    assert(len(sub.modmail) == 2)
    assert(test_submission2.deleted == False)
    assert(len(test_submission2.reports) == 1)

    ###
    # Test3
    ###
    test_submission3 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="asdfg", url="https://youtube.com/watch?v=3")
    test.advance_time_30s()
    # Check conditions are successful for t3
    assert(len(sub.modmail) == 3)
    assert(test_submission3.deleted == True)
    assert(len(test_submission3.reports) == 0)


def test_yt_post_negative(create_bot):
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update control panel and plugin wiki
    sub.edit_wiki("control_panel", yt_plugin)
    sub.edit_wiki("youtube", r"""
    [ch1]
    id = 101

    [ch2]
    id = 102
    message = got a post by some channel ${AUTHOR} ${KIND}
    report = blah
    delete = True

    [ch3]
    id = 103
    delete = True
    """)

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_30s()

    ###
    # Test1
    ###
    test_submission1 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="asdfg", url="https://youtube.com/watch?v=1")
    test.advance_time_30s()

    # Check conditions are successful for t1
    assert(len(sub.modmail) == 0)
    assert(test_submission1.deleted == False)
    assert(len(test_submission1.reports) == 0)

    ###
    # Test2
    ###
    test_submission2 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="asdfg", url="https://youtube.com/watch?v=2")
    test.advance_time_30s()
    # Check conditions are successful for t2
    assert(len(sub.modmail) == 0)
    assert(test_submission2.deleted == False)
    assert(len(test_submission2.reports) == 0)

    ###
    # Test3
    ###
    test_submission3 = test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
                                           title="asdfg", url="https://youtube.com/watch?v=3")
    test.advance_time_30s()
    # Check conditions are successful for t3
    assert(len(sub.modmail) == 0)
    assert(test_submission3.deleted == False)
    assert(len(test_submission3.reports) == 0)

    test.advance_time_30s()
    assert(len(test.get_user("BigDaddy").inbox) == 3)