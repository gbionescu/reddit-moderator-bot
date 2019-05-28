from sqlalchemy import create_engine, Table, Column, String, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import MetaData
from sqlalchemy.pool import StaticPool
import database

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

        # Create built-in tables
        self.create_reddit_tables()


    def create_reddit_tables(self):
        self.comments = Table("comments", database.metadata,
            Column("body",                    String),
            Column("author",                  String),
            Column("aithor_flair_text",       String),
            Column("downs",                   Integer),
            Column("created_utc",             DateTime),
            Column("subreddit_id",            String),
            Column("link_id",                 String),
            Column("parent_id",               String),
            Column("score",                   Integer),
            Column("retrieved_on",            DateTime),
            Column("controversiality",        Integer),
            Column("gilded",                  Integer),
            Column("id",                      String, primary_key=True),
            Column("subreddit",               String),
            Column("ups",                     Integer),
            Column("distinguished",           String),
            Column("author_flair_css_class",  String))

        self.submissions = Table("submissions", database.metadata,
            Column("created_utc",             DateTime),
            Column("subreddit",               String),
            Column("author",                  String),
            Column("domain",                  String),
            Column("url",                     String),
            Column("num_comments",            Integer),
            Column("score",                   Integer),
            Column("ups",                     Integer),
            Column("downs",                   Integer),
            Column("title",                   String),
            Column("selftext",                String),
            Column("id",                      String, primary_key=True),
            Column("gilded",                  Integer),
            Column("stickied",                Boolean),
            Column("retrieved_on",            Integer),
            Column("over_18",                 Boolean),
            Column("thumbnail",               String),
            Column("subreddit_id",            String),
            Column("hide_score",              Boolean),
            Column("link_flair_css_class",    String),
            Column("author_flair_css_class",  String),
            Column("archived",                Boolean),
            Column("is_self",                 Boolean),
            Column("permalink",               String),
            Column("author_flair_text",       String),
            Column("quarantine",              Boolean),
            Column("link_flair_text",         String),
            Column("distinguished",           String))

        database.metadata.create_all(self.db_engine)