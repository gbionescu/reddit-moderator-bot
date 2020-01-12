import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"
enable_streamer = """
[Enabled Plugins]
webhook_streamer
"""

@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)

def test_webhook(create_bot):
    wiki_cfg = """
    [Setup]
    modlog = http://webhook1
    submissions = http://webhook2
    """
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update control panel and plugin wiki
    sub.edit_wiki("control_panel", enable_streamer)
    sub.edit_wiki("webhook_streamer", wiki_cfg)

    # Give some time to the bot to get the new wiki configuration
    test.advance_time_60s()

    # Check that the webhook target is None first
    # (aka does not exist because no messages have been sent)
    assert(test.get_webhook("http://webhook1") == None)

    # Add modlog item
    sub.add_modlog("mod1", "dummy_target", "test", "blabla", "test description")

    # Check again
    assert(len(test.get_webhook("http://webhook1").messages) == 1)

    test.advance_time_60s()


    # Check that the webhook target is None first
    # (aka does not exist because no messages have been sent)
    assert(test.get_webhook("http://webhook2") == None)

    # Create a new submissinon to test submission webhooks too
    test.FakeSubmission(subreddit_name=TEST_SUBREDDIT, author_name="JohnDoe1",
        title="AAAA BBBB CCCC DDDD EEEE FFFF")

    test.advance_time_60s()

    # Check again
    assert(len(test.get_webhook("http://webhook2").messages) == 1)