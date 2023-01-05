| :exclamation:  This repository is now read-only in favor of https://github.com/miquelruiz/yrs |
|-----------------------------------------------------------------------------------------------|

# YouTube RSS Subscriber

YouTube RSS Subscriber (`yrs`) allows you to subscribe to YouTube channels without the
need of a YouTube account.

`yrs` uses a local database (sqlite by default) to keep track of the subscribed channels,
which are updated making use of the RSS feed that YouTube publishes. This update needs to
happen via `yrs update`, running it either manually or via cron.


## Installation

```
pip install youtube-rss-subscriber
```

## Basic usage

First you'll need to subscribe to some channels. Lets subsribe to "This Old Tony" as an example:
```
$ yrs subscribe https://www.youtube.com/user/featony
Config file created in /home/mruiz/.yrs/config.yml
Subscribed to "This Old Tony"
```

If this is the first you run `yrs`, it'll create a config file under your home directory.
By default it also creates an empty sqlite database that will be used to keep track of subscribed
channels and old/new videos. The subscribe command checks the RSS feed for the channel, and records all
the video entries currently published.

After subscribing, the channels and the videos can be listed:
```
$ yrs list-channels
ID                        Name           URL                                     Autodownload
------------------------  -------------  ------------------------------------  --------------
UC5NO8MgTQKHAWXp6z8Xl7yQ  This Old Tony  https://www.youtube.com/user/featony               0

$ yrs list-videos "This Old Tony"
ID           Title                           URL                                          Published
-----------  ------------------------------  -------------------------------------------  -------------------
JN-Pkbeu52E  Consoling a Milling Machine     https://www.youtube.com/watch?v=JN-Pkbeu52E  2020-10-31 20:47:14
...
```

The ID of the videos can be used to download them:
```
$ yrs download JN-Pkbeu52E
[youtube] JN-Pkbeu52E: Downloading webpage
[download] Destination: Consoling a Milling Machine-JN-Pkbeu52E.mp4
[download] 100% of 76.29MiB in 00:09
```

After some time, you will probably want to check if there's anything new on your subscribed channels:
```
$ yrs update
Channel:  This Old Tony
Title:  NOW We're Cook'n with Argon!!
URL:  https://www.youtube.com/watch?v=O_Fo7mfZg7k

Channel:  This Old Tony
Title:  VCARVE Branding / Logo Irons - SECRET SANTA 2020!
URL:  https://www.youtube.com/watch?v=f9qN9LIChh4

Channel:  This Old Tony
Title:  Getting a Handle on Ron Covell
URL:  https://www.youtube.com/watch?v=8zb92v5Vz40
```

To unsubscribe from a channel:
```
$ yrs unsubscribe "This Old Tony"
```