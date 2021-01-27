from typing import Iterator
import sys

from bs4 import BeautifulSoup
import click
import requests
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.sql.expression import or_
from tabulate import tabulate
from youtube_rss_subscriber import config, download, schema


def retrieve_videos(channel: schema.Channel) -> Iterator[schema.Video]:
    r = requests.get(channel.rss)
    soup = BeautifulSoup(r.text, "xml")
    for entry in soup.find_all("entry"):
        yield schema.Video.from_soup(entry, channel)


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
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
def subscribe(
    ctx: click.Context,
    url: str,
    autodownload: bool,
    dryrun: bool,
) -> None:
    session = ctx.obj["dbsession"]
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
        print(f"Couldn't subscribe to {url}. Is the URL correct?", file=sys.stderr)
        sys.exit(1)

    channel.autodownload = autodownload
    session.merge(channel)

    for v in retrieve_videos(channel):
        v.downloaded = 1
        session.merge(v)

    if not dryrun:
        session.commit()
    print(f'Subscribed to "{channel.name}"')


@main.command()
@click.pass_context
@click.option("--dryrun", is_flag=True, default=False)
@click.option("--no-download", is_flag=True, default=False)
def update(ctx: click.Context, dryrun: bool, no_download: bool) -> None:
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
@click.option("--dryrun", is_flag=True, default=False)
def unsubscribe(ctx: click.Context, channel: str, dryrun: bool) -> None:
    session = ctx.obj["dbsession"]

    # Try searching by any of the relevant fields: name, id or url
    query = session.query(schema.Channel).filter(
        or_(
            schema.Channel.name == channel,
            schema.Channel.id == channel,
            schema.Channel.url == channel,
        )
    )

    try:
        channel_obj = query.one()
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

    session.delete(channel_obj)
    if not dryrun:
        session.commit()


if __name__ == "__main__":
    main(obj={})
