import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"

@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)

def test_inbox_help(create_bot):
    test.get_reddit().inbox.add_message("randomuser", "/help")
    test.advance_time_10m()