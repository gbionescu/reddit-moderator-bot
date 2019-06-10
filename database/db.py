import database
import datetime
from sqlalchemy import create_engine, Table, Column, String, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import MetaData
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.declarative import declarative_base

class db_data():
    def __init__(self, db_path):
        self.db_engine = create_engine(db_path, poolclass=StaticPool)
        self.db_factory = sessionmaker(bind=self.db_engine)
        self.db_session = scoped_session(self.db_factory)
        self.db_metadata = MetaData()
        self.db_base = declarative_base(metadata=self.db_metadata, bind=self.db_engine)

        # Set the global objects so that they're used by the plugins
        database.metadata = self.db_metadata
        database.base = self.db_base

        class DBComment(self.db_base):
            __tablename__ = "comments"

            autor                   = Column(String)
            author_flair_css_class  = Column(String)
            author_flair_text       = Column(String)
            body                    = Column(String)
            controversiality        = Column(Integer)
            created_utc             = Column(DateTime)
            distinguished           = Column(String)
            downs                   = Column(Integer)
            gilded                  = Column(Integer)
            id                      = Column(String, primary_key=True)
            link_id                 = Column(String)
            parent_id               = Column(String)
            retrieved_on            = Column(DateTime)
            score                   = Column(Integer)
            subreddit               = Column(String)
            subreddit_id            = Column(String)
            ups                     = Column(Integer)

            def __init__(self, comment):
                self.author                 = comment.author.name
                self.author_flair_css_class = comment.author_flair_css_class
                self.author_flair_text      = comment.author_flair_text
                self.body                   = comment.body
                self.controversiality       = comment.controversiality
                self.created_utc            = datetime.datetime.utcfromtimestamp(comment.created_utc)
                self.distinguished          = comment.distinguished
                self.downs                  = comment.downs
                self.gilded                 = comment.gilded
                self.id                     = comment.id
                self.link_id                = comment.link_id
                self.parent_id              = comment.parent_id
                self.retrieved_on           = datetime.datetime.utcnow()
                self.score                  = comment.score
                self.subreddit              = comment.subreddit.name
                self.subreddit_id           = comment.subreddit_id
                self.ups                    = comment.ups

        class DBSubmission(self.db_base):
            archived                = Column(Boolean)
            author                  = Column(String)
            author_flair_css_class  = Column(String)
            author_flair_text       = Column(String)
            created_utc             = Column(DateTime)
            distinguished           = Column(String)
            domain                  = Column(String)
            downs                   = Column(Integer)
            gilded                  = Column(Integer)
            id                      = Column(String, primary_key=True)
            is_self                 = Column(Boolean)
            hide_score              = Column(Boolean)
            link_flair_css_class    = Column(String)
            link_flair_text         = Column(String)
            num_comments            = Column(Integer)
            over_18                 = Column(Boolean)
            permalink               = Column(String)
            quarantine              = Column(Boolean)
            retrieved_on            = Column(Integer)
            score                   = Column(Integer)
            selftext                = Column(String)
            stickied                = Column(Boolean)
            subreddit               = Column(String)
            subreddit_id            = Column(String)
            title                   = Column(String)
            thumbnail               = Column(String)
            url                     = Column(String)
            ups                     = Column(Integer)


            def __init__(self, sub):
                self.archived               = sub.archived
                self.author                 = sub.author.name
                self.author_flair_css_class = sub.author_flair_css_class
                self.author_flair_text      = sub.author_flair_text
                self.created_utc            = datetime.datetime.utcfromtimestamp(sub.created_utc)
                self.distinguished          = sub.distinguished
                self.domain                 = sub.domain
                self.downs                  = sub.downs
                self.gilded                 = sub.gilded
                self.id                     = sub.id
                self.is_self                = sub.is_self
                self.hide_score             = sub.hide_score
                self.link_flair_css_class   = sub.link_flair_css_class
                self.link_flair_text        = sub.link_flair_text
                self.num_comments           = sub.num_comments
                self.over_18                = sub.over_18
                self.permalink              = sub.permalink
                self.quarantine             = sub.quarantine
                self.retrieved_on           = datetime.datetime.utcnow()
                self.score                  = sub.score
                self.selftext               = sub.selftext
                self.stickied               = sub.stickied
                self.subreddit              = sub.subreddit
                self.subreddit_id           = sub.subreddit_id
                self.title                  = sub.title
                self.thumbnail              = sub.thumbnail
                self.url                    = sub.url
                self.ups                    = sub.ups


        self.DBComment = DBComment
        self.DBSubmission = DBSubmission

        # Create built-in tables
        self.create_reddit_tables()

    def create_reddit_tables(self):
        # self.submissions = Table("submissions", self.db_metadata,
        #     Column("created_utc",             DateTime),
        #     Column("subreddit",               String),
        #     Column("author",                  String),
        #     Column("domain",                  String),
        #     Column("url",                     String),
        #     Column("num_comments",            Integer),
        #     Column("score",                   Integer),
        #     Column("ups",                     Integer),
        #     Column("downs",                   Integer),
        #     Column("title",                   String),
        #     Column("selftext",                String),
        #     Column("id",                      String, primary_key=True),
        #     Column("gilded",                  Integer),
        #     Column("stickied",                Boolean),
        #     Column("retrieved_on",            Integer),
        #     Column("over_18",                 Boolean),
        #     Column("thumbnail",               String),
        #     Column("subreddit_id",            String),
        #     Column("hide_score",              Boolean),
        #     Column("link_flair_css_class",    String),
        #     Column("author_flair_css_class",  String),
        #     Column("archived",                Boolean),
        #     Column("is_self",                 Boolean),
        #     Column("permalink",               String),
        #     Column("author_flair_text",       String),
        #     Column("quarantine",              Boolean),
        #     Column("link_flair_text",         String),
        #     Column("distinguished",           String))

        database.metadata.create_all(self.db_engine)

    def add_comment(self, comment):
        self.db_session.add(self.DBComment(comment))
        self.db_session.commit()


    #def add_submission(self, submission):
