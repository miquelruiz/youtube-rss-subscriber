from typing import Any, Iterator
import sys

from bs4 import BeautifulSoup
import click
import requests

from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker

from youtube_rss_subscriber import config, download, schema


def retrieve_videos(channel: schema.Channel) -> Iterator[schema.Video]:
    r = requests.get(channel.rss)
    soup = BeautifulSoup(r.text, "xml")
    for entry in soup.find_all("entry"):
        yield schema.Video.from_soup(entry, channel)


@click.group()
@click.pass_context
def main(ctx: Any) -> None:
    try:
        conf = config.Config()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    engine = create_engine(conf.database_url)
    session = sessionmaker(bind=engine)()
    schema.ensure_schema(engine)

    ctx.ensure_object(dict)
    ctx.obj["dbsession"] = session


@main.command()
@click.pass_context
@click.argument("url")
@click.option("--autodownload/--no-autodownload", default=True)
@click.option("--dryrun", is_flag=True, default=False)
def subscribe(ctx: Any, url: str, autodownload: bool, dryrun: bool) -> None:
    session = ctx.obj["dbsession"]
    try:
        r = requests.get(url)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(r.text, "html.parser")
    channel = schema.Channel.from_soup(soup, url)
    channel.autodownload = autodownload
    session.merge(channel)

    for v in retrieve_videos(channel):
        v.downloaded = 1
        session.merge(v)

    if not dryrun:
        session.commit()
    print(f"Subscribed to \"{channel.name}\"")


@main.command()
@click.pass_context
@click.option("--dryrun", is_flag=True, default=False)
@click.option("--no-download", is_flag=True, default=False)
def update(ctx: Any, dryrun: bool, no_download: bool) -> None:
    session = ctx.obj["dbsession"]
    for channel in session.query(schema.Channel).all():
        for video in retrieve_videos(channel):
            if not session.query(schema.Video).filter_by(id=video.id).first():
                print("Channel: ", video.channel.name)
                print("Title: ", video.title)
                print("URL: ", video.url)

                if channel.autodownload:
                    download.download(video.url, dryrun=dryrun or no_download)
                    video.downloaded = 1
                else:
                    video.downloaded = 0

                print()
                session.merge(video)
    if not dryrun:
        session.commit()


if __name__ == "__main__":
    main(obj={})
