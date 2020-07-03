# TKLServer - Discord webhook integration for TKLMutator

TKLServer is a server for [TKLMutator](https://github.com/tuokri/rs2-tklogging)
for Discord webhook integration. TKLServer could also be called a Discord bot as it
serves a similar purpose.
TKLMutator is a Rising Storm 2: Vietnam server mutator, which provides kill logging
utilities for server administrators.

**Q:** Why is TKLServer needed?

**A:** RS2: Vietnam mods (or rather the Unreal Engine version the game uses)
do not support HTTPS, which is required for Discord webhooks.

## Installation option 1 (requires Git + Python 3.6 or newer)

1. Clone TKLServer repository:

    `git clone https://github.com/tuokri/tklserver`

    `cd tklserver`

2. Install requirements:

    `pip install -r requirements.txt`

3. Run the TKLServer:

    `python run.py`

4. Start RS2: Vietnam game server with TKLMutator enabled.

## Installation option 2 (download repository zip, Python 3.6 or newer required)

1. Download [repository package (zip)](https://github.com/tuokri/tklserver/archive/master.zip)
and extract it. Then follow the same steps as option 1 but ignore the `git clone` command.

## Installation option 3 (download executable, no Python or Git needed)

1. Download latest package from [releases](https://github.com/tuokri/tklserver/releases).

2. Extract it and run `tklserver.exe`.

## Updating

If you used Git to install TKLServer, do a `git pull` in the TKLServer directory.
Alternatively you can just download the newest one and extract
it over the old files.

Double-check your settings in `tklserver.ini` after updating.

## Configuration examples

### One RS2 server and one Discord webhook URL

One RS2: Vietnam game server process and one TKLServer process on the
same dedicated server machine.

![1-server-1-webhook](1-server-1-webhook.png)

**tklserver.ini** (in tklserver directory)
```ini
[tklserver]
port=8586
host=localhost

[rs2server.0000]
webhook_url=YOUR_SECRET_DISCORD_WEBHOOK_URL_HERE
```

**ROMutator_TKLMutator_Server.ini** (in RS2 server directory under `ROGame\Config`).
If the file does not exists, launch RS2 game server once with TKLMutator enabled.

```ini
[TKLMutator.TKLMutator]
bLogTeamKills=True
bLogKills=False
bSendLogToServer=True
TKLFileName=KillLog

[TKLMutator.TKLMutatorTcpLinkClient]
TKLServerHost=localhost
TKLServerPort=8586
MaxRetries=5
UniqueRS2ServerId=0000
```

`UniqueRS2ServerId` in **ROGame_TKLMutator.ini** references `[rs2server.0000]` in **tklserver.ini**.
This needs to change only when support for multiple RS2: Vietnam game servers is needed.

`TKLServerPort` in **ROGame_TKLMutator.ini** must match `port` in **tklserver.ini**.

`bSendLogToServer` must be `True` in **ROGame_TKLMutator.ini**.

---

**More configuration examples coming soon.**
