# TKLServer - Discord webhook integration for TKLMutator

Server for [TKLMutator](https://github.com/tuokri/rs2-tklogging)
for Discord webhook integration.
TKLMutator is a Rising Storm 2: Vietnam server mutator, which provides utilities 
for server administrators.

**Q:** Why is TKLServer needed?

**A:** RS2: Vietnam mods do not support HTTPS, which is required for
Discord webhooks.

### Installation option 1 (Requires Git + Python 3.6 or newer)

Clone TKLserver repository with:

`git clone https://github.com/tuokri/tklserver`

Run the server:

`python run.py`

### Installation option 2 (Download executable)

STANDALONE SERVER EXECUTABLE (.exe) COMING SOON.

### Configuration examples

##### 1 RS2 server and 1 Discord webhook URL

1 RS2 game server process and 1 TKLServer process in the
same dedicated server machine.

![1-server-1-webhook](1-server-1-webhook.png)

**tklserver.ini**
```ini
[tklserver]
port=8586
host=localhost

[rs2server.0000]
webhook_url=YOUR_SECRET_DISCORD_WEBHOOK_URL_HERE
```

**ROGame_TKLMutator.ini**
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
