import datetime
import re
import socket
import sys
import threading
from collections import defaultdict
from configparser import ConfigParser
from socketserver import StreamRequestHandler
from socketserver import ThreadingTCPServer
from typing import Optional
from typing import Tuple

import discord
import logbook
import pytz
import requests
from discord import RequestsWebhookAdapter
from discord import Webhook
from logbook import Logger
from logbook.handlers import RotatingFileHandler
from logbook.handlers import StreamHandler

StreamHandler(
    sys.stdout, level="INFO", bubble=True).push_application()
RotatingFileHandler(
    "tklserver.log", level="INFO", bubble=True).push_application()
logger = Logger("tklserver")
logbook.set_datetime_format("local")

STEAM_PROFILE_URL = "https://www.steamcommunity.com/profiles/{id}"
DATE_FMT = "%Y/%m/%d - %H:%M:%S"
TKL_MSG_PAT = re.compile(
    r"\(([0-9]{4}/[0-9]{2}/[0-9]{2}\s-\s[0-9]{2}:[0-9]{2}:[0-9]{2})\)\s'(.+)'\s"
    r"\[(0x[0-9a-fA-F]+)\]\s(killed|teamkilled)\s'(.+)'\s\[(0x[0-9a-fA-F]+)\]\swith\s<(.+)>")
SEP = "\n\r"
BSEP = SEP.encode("utf-8")


class TKLServer(ThreadingTCPServer):
    daemon_threads = True

    def __init__(self, *args, stop_event: threading.Event,
                 discord_config: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = stop_event
        self._discord_config = discord_config

    @property
    def stop_requested(self) -> bool:
        return self._stop_event.is_set()

    @property
    def discord_config(self) -> dict:
        return self._discord_config


class TKLRequestHandler(StreamRequestHandler):
    def __init__(self, request, client_address, server: TKLServer):
        self.server: TKLServer = server
        super().__init__(request, client_address, server)

    def execute_webhook(self, ident: str, msg: str):
        # TODO: embed kill weapon image.

        embed: Optional[discord.Embed] = None
        try:
            msg_match = TKL_MSG_PAT.match(msg)
            groups = msg_match.groups()
            if not msg_match:
                logger.warn("message does not match pattern")
            else:
                date = groups[0]
                date = datetime.datetime.strptime(date, DATE_FMT)
                date = date.astimezone(pytz.utc)

                killer = groups[1]
                killer_id = int(groups[2], 16)
                killer_profile = STEAM_PROFILE_URL.format(id=killer_id)
                killed = groups[4]
                killed_id = int(groups[5], 16)
                killed_profile = STEAM_PROFILE_URL.format(id=killed_id)
                damage_type = groups[6]

                action = groups[3]
                if killed_id == killer_id:
                    action = "suicide"
                    damage_type = damage_type.replace("SUICIDE_", "")

                action_formatted = {
                    "killed": "Kill",
                    "teamkilled": "Team Kill",
                    "suicide": "Suicide",
                }[action]

                color = {
                    "killed": 3066993,
                    "teamkilled": 15158332,
                    "suicide": 9807270,
                }[action]

                if killer_id == 0:
                    killer_id_link = "BOT"
                else:
                    killer_id_link = f"[{killer_id}]({killer_profile})"
                if killed_id == 0:
                    killed_id_link = "BOT"
                else:
                    killed_id_link = f"[{killed_id}]({killed_profile})"

                # Both are bots. Avoid false "Suicide".
                if (killed_id == 0) and (killer_id == 0):
                    action_formatted = "Bot Killed Bot"

                embed = discord.Embed(
                    title=action_formatted,
                    timestamp=date,
                    color=color,
                ).add_field(
                    name="Killer",
                    value=killer,
                    inline=True,
                ).add_field(
                    name="Victim",
                    value=killed,
                    inline=True,
                ).add_field(
                    name="\u200b",
                    value="\u200b",
                ).add_field(
                    name="Killer ID",
                    value=killer_id_link,
                    inline=True,
                ).add_field(
                    name="Victim ID",
                    value=killed_id_link,
                    inline=True,
                ).add_field(
                    name="\u200b",
                    value="\u200b",
                ).add_field(
                    name="Damage Type",
                    value=damage_type,
                )

        except Exception as e:
            logger.error("error creating embed message: {e}",
                         e=e, exc_info=True)

        webhook_id = self.server.discord_config[ident][0]
        webhook_token = self.server.discord_config[ident][1]
        webhook = Webhook.partial(
            id=webhook_id, token=webhook_token, adapter=RequestsWebhookAdapter()
        )

        if embed is not None:
            logger.info("sending webhook embed for {i}", i=ident)
            webhook.send(embed=embed)
        else:
            logger.info("sending webhook message for {i}", i=ident)
            webhook.send(content=msg)

    def handle(self):
        try:
            logger.info("connection opened from: {sender}",
                        sender=self.client_address)
            while not self.server.stop_requested:
                data = self.rfile.readline()
                if data.startswith(b"\x00") or not data:
                    logger.info(
                        "received quit request from {sender}, closing connection",
                        sender=self.client_address)
                    break
                logger.debug("raw data: {data}", data=data)

                data = str(data, encoding="utf-8").strip()
                ident = data[:4]
                data = data[4:]
                logger.debug("{i}: {data}", i=ident, data=data)
                if ident in self.server.discord_config:
                    self.execute_webhook(ident, data)
                else:
                    logger.error("server unique ID {i} not in Discord config", i=ident)
        except (ConnectionError, socket.error) as e:
            logger.error("{sender}: connection error: {e}",
                         sender=self.client_address, e=e)
        except Exception as e:
            logger.error("error when handling request from {addr}: {e}",
                         addr=self.client_address, e=e)


def parse_webhook_url(url: str) -> Tuple[int, str]:
    resp = requests.get(url).json()
    _id = int(resp["id"])
    token = resp["token"]
    return _id, token


def load_config() -> dict:
    cp = ConfigParser()
    cp.read("tklserver.ini")
    sections = cp.sections()

    ret = defaultdict(dict, cp)
    for section in sections:
        if section.startswith("rs2server"):
            ident = section.split(".")[1]
            url = cp[section].get("webhook_url")
            try:
                ret["discord"][ident] = parse_webhook_url(url)
            except Exception as e:
                logger.error("webhook URL failure for RS2 server ID={i}: {e}",
                             i=ident, e=e)

    return ret


def terminate(stop_event: threading.Event):
    stop_event.set()


def main():
    config = load_config()

    try:
        server_config = config["tklserver"]
        port = server_config.getint("port")
        host = server_config["host"]
        if not port:
            logger.error("port not set, exiting...")
            sys.exit(-1)
    except (ValueError, KeyError) as e:
        logger.debug("invalid config: {e}", e=e, exc_info=True)
        logger.error("invalid config, exiting...")
        sys.exit(-1)

    stop_event = threading.Event()
    addr = (host, port)
    server = None
    try:
        server = TKLServer(addr, TKLRequestHandler, stop_event=stop_event,
                           discord_config=config["discord"])
        logger.info("serving at: {host}:{port}", host=addr[0], port=addr[1])
        logger.info("press CTRL+C to shut down the server")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("server stop requested")
    finally:
        if server:
            t = threading.Thread(target=terminate, args=(stop_event,))
            t.start()
            t.join()
            server.shutdown()
            server.server_close()

    logger.info("server shut down successfully")


if __name__ == "__main__":
    main()
