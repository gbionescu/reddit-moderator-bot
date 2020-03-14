import pytest
import modbot.input.test as test

TEST_SUBREDDIT = "testsub123"

@pytest.fixture
def create_bot():
    test.create_bot(TEST_SUBREDDIT)

def test_create_post(create_bot):
    # Test basic commands
    test.get_reddit().inbox.add_message(
        "mod1",
        "/create_post --subreddit=ble --sticky --title=test --body='asd\nxxx'")
    test.advance_time_10m()

    _, body = test.get_user("mod1").inbox[0]

    # Get first line
    fline = body.split("\n")[0]

    # Get id
    target_sub = None
    id = fline.split(" ")[1]
    for sub in test.cache_submissions.values():
        if sub.shortlink == id:
            target_sub = sub

    # Create comments
    comm1 = target_sub.add_comment("asd", "xxx1")
    comm2 = target_sub.add_comment("asd", "qwe1")

    # Tell the bot to add them
    test.get_reddit().inbox.add_message(
        "mod1",
        "/integrate_comment --sub_link %s --comment_link %s" % \
            (target_sub.shortlink, comm1.permalink))
    test.get_reddit().inbox.add_message(
        "mod1",
        "/integrate_comment --sub_link %s --comment_link %s" % \
            (target_sub.shortlink, comm2.permalink))

    # Check if added
    test.advance_time_10m()
    assert "xxx1" in target_sub.body
    assert "qwe1" in target_sub.body

    # Edit and check again
    comm1.edit("xxx2")
    comm2.edit("qwe2")

    # Check if added again
    test.advance_time_10m()
    assert "xxx2" in target_sub.body
    assert "qwe2" in target_sub.body

    test.get_reddit().inbox.add_message(
        "mod1",
        "/nointegrate_comment --sub_link %s --comment_link %s" % \
            (target_sub.shortlink, comm1.permalink))

    # Check if added again
    test.advance_time_10m()
    assert "xxx2" not in target_sub.body
    assert "qwe2" in target_sub.body

    # Unsticky the comment
    target_sub.mod.sticky(False, False)

    # Edit the comments
    comm2.edit("qwe3")

    # Make sure that comments were not added
    test.advance_time_10m()
    assert "qwe2" in target_sub.body

    # resticky the comment
    test.get_reddit().inbox.add_message(
        "mod1",
        "/resticky --sub_link %s" % (target_sub.shortlink))

    # Check if it was updated
    test.advance_time_10m()
    assert "qwe3" in target_sub.body