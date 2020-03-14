import pytest
import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"
enable_wiki = """
[Enabled Plugins]
change_sidebar
"""

wiki_content = """
[Setup]
123 = https://123.com
456 = https://456.com
"""

sub_decr = """
qweqweq
[](/begin-pics)
[](/end-pics)
qeqweqew
"""

@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)

def test_sidebar_pic(create_bot):
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Update control panel and plugin wiki
    sub.edit_wiki("control_panel", enable_wiki)
    sub.edit_wiki("change_sidebar", wiki_content)
    # Set fake sidebar
    sub.edit_wiki("config/sidebar", sub_decr)
    test.advance_time_10m()

    # Jump in time 23 hours and simulate one
    test.advance_time(60 * 60 * 23)
    test.advance_time_1h()
    assert(sub.widgets.sidebar[0].mod.data[0]["linkUrl"] == "https://www.reddit.com/r/123")

    # Jump in time 23 hours and simulate one
    test.advance_time(60 * 60 * 23)
    test.advance_time_1h()
    assert(sub.widgets.sidebar[0].mod.data[0]["linkUrl"] == "https://www.reddit.com/r/456")