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
        "/create_post --subreddit=testsub123 --sticky --title test1 test2 test3 --body zzz ddd")
    test.advance_time_10m()

    _, body = test.get_user("mod1").inbox[-1]

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
        "/integrate_comment --sub_link %s --comment_link %s" %
        (target_sub.shortlink, comm1.permalink))
    test.get_reddit().inbox.add_message(
        "mod1",
        "/integrate_comment --sub_link %s --comment_link %s" %
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
        "/nointegrate_comment --sub_link %s --comment_link %s" %
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


def test_clone_post(create_bot):
    # Test cloned post
    test_submission = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="title_test",
        body="asd1234")

    test.get_reddit().inbox.add_message(
        "mod1",
        "/clone_post --subreddit=testsub123 --sticky --title=test2 --sub_link=%s" % test_submission.shortlink)
    test.advance_time_10m()

    _, body = test.get_user("mod1").inbox[-1]

    # Get first line
    fline = body.split("\n")[0]

    # Get id
    target_sub = None
    id = fline.split(" ")[1]
    for sub in test.cache_submissions.values():
        if sub.shortlink == id:
            target_sub = sub

    # Check for content
    assert "asd1234" in target_sub.body

    # Edit the original body
    test_submission.edit("asd5678")

    test.advance_time_10m()

    # Check for content
    assert "asd5678" in target_sub.body


def test_create_from_wiki(create_bot):
    content = """
    content

    multi

    line
    """
    sub = test.get_subreddit(TEST_SUBREDDIT)

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    # Update control panel and plugin wiki
    sub.edit_wiki("wiki123", content)

    test.get_reddit().inbox.add_message(
        "mod1",
        "/create_post --subreddit=%s --sticky --title=test --wikibody=wiki123" % TEST_SUBREDDIT)
    test.advance_time_10m()

    _, body = test.get_user("mod1").inbox[-1]

    # Get first line
    fline = body.split("\n")[0]

    # Get id
    target_sub = None
    id = fline.split(" ")[1]
    for s in test.cache_submissions.values():
        if s.shortlink == id:
            target_sub = s

    # Check for a word
    assert "multi" in target_sub.body

    # Edit the wiki
    sub.edit_wiki("wiki123", content + "XXX")

    # Check it again
    test.advance_time_10m()
    assert "XXX" in target_sub.body


def test_sched_post(create_bot):
    enable_sched_posts = """
    [Enabled Plugins]
    schedule_posts
    """

    sub = test.get_subreddit(TEST_SUBREDDIT)

    test.set_time(22 * 60 * 60)
    test_submission = test.FakeSubmission(
        subreddit_name=TEST_SUBREDDIT,
        author_name="JohnDoe1",
        title="title_test",
        body="asd1234")

    wiki_sched_posts = r"""
    [post_at_12AM]
    title=test1 test2 ${DAY}.${MONTH}.${YEAR}
    body=aaa
     bbb
     ccc
    interval= 0 0 * * * *

    [post_at_1AM]
    title=test3 test4
    wikibody=post1AM
    interval= 0 1 * * * *

    [post_at_2AM]
    title=test5 test6
    clonepost=%s
    interval= 0 2 * * * *
    """ % test_submission.permalink

    sub.edit_wiki("post1AM", "xx1")

    # Update control panel and plugin wiki
    sub.edit_wiki("control_panel", enable_sched_posts)
    sub.edit_wiki("schedule_posts", wiki_sched_posts)

    # Tell the bot to update the control panel
    test.get_reddit().inbox.add_message(
        "mod1", "/update_control_panel --subreddit %s" % TEST_SUBREDDIT)

    test.advance_time_10m()

    test.advance_time_1h()
    test.advance_time_1h()
    test.advance_time_1h()
    test.advance_time_1h()

    post_12am = None
    post_1am = None
    post_2am = None

    # Get the posts
    for post in test.cache_submissions.values():
        if post.title.startswith("test1 test2"):
            post_12am = post

        if post.title == "test3 test4":
            post_1am = post

        if post.title == "test5 test6":
            post_2am = post

    assert post_12am
    assert post_1am
    assert post_2am

    assert post_12am.created_utc - 86400 < 60
    assert post_1am.created_utc - 90000 < 60
    assert post_2am.created_utc - 93600 < 60
