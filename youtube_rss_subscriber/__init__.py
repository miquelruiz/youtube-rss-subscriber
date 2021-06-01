import logging
from typing import Collection
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
import click
import requests
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker, Session
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.sql.expression import or_
from sqlalchemy.sql.operators import as_
from tabulate import tabulate
from youtube_rss_subscriber import config, download as dl, schema


log: logging.Logger = logging.getLogger(__name__)


def retrieve_videos(channel: schema.Channel) -> Collection[schema.Video]:
    r = requests.get(channel.rss)
    soup = BeautifulSoup(r.text, "xml")
    return [schema.Video.from_soup(entry, channel) for entry in soup.find_all("entry")]


def find_unique_channel(session: Session, channel_str: str) -> schema.Channel:
    # Try searching by any of the relevant fields: name, id or url
    query = session.query(schema.Channel).filter(
        or_(
            schema.Channel.name == channel_str,
            schema.Channel.id == channel_str,
            schema.Channel.url == channel_str,
        )
    )

    try:
        channel = query.one()
    except MultipleResultsFound:
        print(
            "The given channel is ambiguous, try again with the channel id",
            file=sys.stderr,
        )
        rows = []
        for c in query:
            rows.append([c.id, c.name, c.url])
        print(tabulate(rows, headers=["ID", "Name", "URL"]), file=sys.stderr)
        sys.exit(1)

    except NoResultFound:
        print("The given channel couldn't be found", file=sys.stderr)
        sys.exit(1)

    return channel


def add_and_scan_channel(
    session: Session,
    channel: schema.Channel,
    autodownload: bool,
    dryrun: bool,
) -> None:
    channel.autodownload = autodownload
    session.merge(channel)

    try:
        videos = retrieve_videos(channel)
    except Exception as e:
        print(f"Couldn't retrieve videos: {e}", file=sys.stderr)
        return

    for v in videos:
        v.downloaded = 1
        session.merge(v)

    if not dryrun:
        session.commit()
    print(f'Subscribed to "{channel.name}"')


@click.group()
@click.pass_context
@click.option("--debug", is_flag=True, default=False)
def main(ctx: click.Context, debug: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    if debug:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

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
    ctx.obj["debug"] = debug


@main.command()
@click.pass_context
@click.argument("url")
@click.option("--autodownload/--no-autodownload", default=False)
@click.option("--dryrun", is_flag=True, default=False)
def subscribe(
    ctx: click.Context,
    url: str,
    autodownload: bool,
    dryrun: bool,
) -> None:
    try:
        r = requests.get(url)
        r.raise_for_status()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(r.text, "html.parser")
    try:
        channel = schema.Channel.from_soup(soup, url)
    except Exception:
        msg = f"Couldn't subscribe to {url}. Try with 'subscribe-by-id'"
        if ctx.obj["debug"]:
            log.exception(msg)
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)

    add_and_scan_channel(ctx.obj["dbsession"], channel, autodownload, dryrun)


@main.command()
@click.pass_context
@click.argument("channel_id")
@click.argument("name")
@click.option("--autodownload/--no-autodownload", default=False)
@click.option("--dryrun", is_flag=True, default=False)
def subscribe_by_id(
    ctx: click.Context, channel_id: str, name: str, autodownload: bool, dryrun: bool
) -> None:
    url = f"https://www.youtube.com/channel/{channel_id}"
    rss = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    channel = schema.Channel(
        id=channel_id,
        url=url,
        name=name,
        rss=rss,
        autodownload=autodownload,
    )
    add_and_scan_channel(ctx.obj["dbsession"], channel, autodownload, dryrun)


@main.command()
@click.pass_context
@click.option("--dryrun", is_flag=True, default=False)
@click.option("--download/--no-download", default=True)
def update(ctx: click.Context, dryrun: bool, download: bool) -> None:
    session = ctx.obj["dbsession"]
    futures = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for channel in session.query(schema.Channel).all():
            f = pool.submit(retrieve_videos, channel)
            futures[f] = channel

        for f in as_completed(futures.keys()):
            try:
                videos = f.result()
            except Exception as e:
                print(f"Couldn't retrieve videos: {e}", file=sys.stderr)
                return

            channel = futures[f]
            for video in videos:
                if not session.query(schema.Video).filter_by(id=video.id).first():
                    print("Channel: ", channel.name)
                    print("Title: ", video.title)
                    print("URL: ", video.url)

                    if download and channel.autodownload:
                        dl.download(video.url, dryrun=dryrun)
                        video.downloaded = 1
                    else:
                        video.downloaded = 0

                    print()
                    session.merge(video)
    if not dryrun:
        session.commit()


@main.command()
@click.pass_context
def list_channels(ctx: click.Context) -> None:
    session = ctx.obj["dbsession"]
    rows = []
    for channel in session.query(schema.Channel):
        rows.append(
            [
                channel.id,
                channel.name,
                channel.url,
                channel.autodownload,
            ]
        )
    print(tabulate(rows, headers=["ID", "Name", "URL", "Autodownload"]))


@main.command()
@click.pass_context
@click.argument("channel")
def list_videos(ctx: click.Context, channel: str) -> None:
    session = ctx.obj["dbsession"]
    channel_obj = find_unique_channel(session, channel)

    rows = []
    for v in channel_obj.videos:
        rows.append([v.id, v.title, v.url, v.published, v.downloaded])

    print(tabulate(rows, headers=["ID", "Title", "URL", "Published", "Downloaded"]))


@main.command()
@click.pass_context
def list_all_videos(ctx: click.Context) -> None:
    session = ctx.obj["dbsession"]
    print(
        tabulate(
            [
                [v.id, v.channel.name, v.title, v.url, v.published]
                for v in session.query(schema.Video)
            ],
            headers=["ID", "Channel", "Title", "URL", "Published"],
        )
    )


@main.command()
@click.pass_context
@click.argument("channel")
@click.option("--dryrun", is_flag=True, default=False)
def unsubscribe(ctx: click.Context, channel: str, dryrun: bool) -> None:
    session = ctx.obj["dbsession"]
    channel_obj = find_unique_channel(session, channel)
    session.delete(channel_obj)
    if not dryrun:
        session.commit()


@main.command()
@click.pass_context
@click.argument("video_id")
@click.option("--dryrun", is_flag=True, default=False)
def download(ctx: click.Context, video_id: str, dryrun: bool) -> None:
    session = ctx.obj["dbsession"]
    video = session.query(schema.Video).filter_by(id=video_id).one_or_none()
    if not video:
        print("The video ID provided was not found", file=sys.stderr)
        sys.exit(1)
    dl.download(video.url, dryrun=dryrun)


@main.command()
@click.pass_context
@click.argument("channel")
@click.option("--enable/--disable", is_flag=True, required=True)
@click.option("--dryrun", is_flag=True, default=False)
def autodownload(ctx: click.Context, channel: str, enable: bool, dryrun: bool) -> None:
    session = ctx.obj["dbsession"]
    channel_obj = find_unique_channel(session, channel)
    channel_obj.autodownload = 1 if enable else 0
    if not dryrun:
        session.commit()


if __name__ == "__main__":
    main(obj={})
