import copy
import youtube_dl
from youtube_rss_subscriber.config import Config


def download(url: str, dryrun: bool = False) -> None:
    opts = copy.deepcopy(Config().youtube_dl_opts)
    if dryrun:
        opts["simulate"] = True
    with youtube_dl.YoutubeDL(opts) as ydl:
        ydl.download([url])
