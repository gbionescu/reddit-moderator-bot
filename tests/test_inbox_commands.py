import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"

@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)

def test_inbox_help(create_bot):
    # Test basic commands
    test.get_reddit().inbox.add_message("randomuser", "/help")
    test.advance_time_10m()
    test.get_reddit().inbox.add_message("randomuser", "/ping")
    test.advance_time_10m()
    # Test unauthrized command
    test.get_reddit().inbox.add_message("randomuser", "/system_status")
    test.advance_time_10m()
    assert(len(test.get_user("randomuser").inbox) == 2)

    test.get_reddit().inbox.add_message("bot_owner", "/help")
    test.advance_time_10m()
    test.get_reddit().inbox.add_message("bot_owner", "/system_status")
    test.advance_time_10m()

    assert(len(test.get_user("bot_owner").inbox) == 5)