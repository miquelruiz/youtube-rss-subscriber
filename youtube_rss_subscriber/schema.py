import dateutil.parser
from typing import Any

from bs4 import BeautifulSoup
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class Channel(Base):  # type: ignore
    __tablename__ = "channels"

    id = Column(String(64), primary_key=True)
    url = Column(String(256), nullable=False)
    name = Column(String(64), nullable=False)
    rss = Column(String(256), nullable=False)
    autodownload = Column(Integer, nullable=False)
    videos = relationship(  # type: ignore
        "Video", cascade="all,delete-orphan", back_populates="channel"
    )

    @staticmethod
    def rss_filter(tag: Any) -> bool:
        return (
            tag.name == "link"
            and "alternate" in tag.get("rel", [])
            and "application/rss+xml" in tag.get("type", [])
            and "RSS" in tag.get("title", [])
        )

    @staticmethod
    def name_filter(tag: Any) -> bool:
        return tag.name == "meta" and "name" in tag.get("itemprop", [])

    @staticmethod
    def channel_id_filter(tag: Any) -> bool:
        return tag.name == "meta" and "channelId" in tag.get("itemprop", [])

    @classmethod
    def from_soup(cls, soup: BeautifulSoup, url: str) -> "Channel":
        channel_id = soup.find_all(cls.channel_id_filter).pop()["content"]
        name = soup.find_all(cls.name_filter).pop()["content"]
        rss = soup.find_all(cls.rss_filter).pop()["href"]

        return cls(id=channel_id, url=url, name=name, rss=rss)


class Video(Base):  # type: ignore
    __tablename__ = "videos"

    id = Column(String(64), primary_key=True)
    url = Column(String(256), nullable=False)
    title = Column(String(256), nullable=False)
    published = Column(DateTime, nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    downloaded = Column(Integer, nullable=False)
    channel = relationship("Channel", back_populates="videos")  # type: ignore

    @classmethod
    def from_soup(cls, soup: BeautifulSoup, channel: Channel) -> "Video":
        return Video(
            id=soup.find_all(["yt:videoid", "yt:videoId"]).pop().text,
            url=soup.link["href"],
            title=soup.title.text,
            published=dateutil.parser.isoparse(soup.published.text),
            channel_id=channel.id,
            downloaded=0,
        )


def ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
