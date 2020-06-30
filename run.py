import socket
import sys
import threading
from collections import defaultdict
from configparser import ConfigParser
from socketserver import BaseRequestHandler
from socketserver import ThreadingTCPServer
from typing import Tuple

import discord
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


class TKLRequestHandler(BaseRequestHandler):
    def __init__(self, request, client_address, server: TKLServer):
        self.server: TKLServer = server
        super().__init__(request, client_address, server)

    def execute_webhook(self, ident: str, msg: str):
        logger.info("sending webhook message for {i}", i=ident)
        webhook_id = self.server.discord_config["ident"][0]
        webhook_token = self.server.discord_config["ident"][1]
        webhook = Webhook.partial(
            id=webhook_id, token=webhook_token, adapter=RequestsWebhookAdapter()
        )
        webhook.send(msg)

    def handle(self):
        try:
            logger.info("connection opened from: {sender}",
                        sender=self.client_address)
            while not self.server.stop_requested:
                data = self.request.recv(1024)
                if data.startswith(b"\x00") or not data:
                    logger.info(
                        "received quit request from {sender}, closing connection",
                        sender=self.client_address)
                    self.request.close()
                    break
                ident = data[:4]
                data = data[4:]
                logger.debug("{i}: {data}", i=ident, data=data)
                if ident in self.server.discord_config:
                    wh_id, wh_token = self.server.discord_config[ident]
                    msg = data.decode("utf-8")
                    send_webhook_message(wh_id, wh_token, msg)
                else:
                    logger.error("server unique ID {i} not in Discord config", i=ident)
        except (ConnectionError, socket.error) as e:
            logger.error("{sender}: connection error: {e}",
                         sender=self.client_address, e=e)
        except Exception as e:
            logger.error("error when handling request from {addr}: {e}",
                         addr=self.client_address, e=e)


def send_webhook_message(webhook_id: int, webhook_token: str, message: str):
    message = discord.utils.escape_mentions(message)
    message = discord.utils.escape_markdown(message)

    webhook = Webhook.partial(
        id=webhook_id, token=webhook_token, adapter=RequestsWebhookAdapter()
    )
    logger.info("sending chat message to Discord length={lm}", lm=len(message))
    webhook.send(message)


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
        listen_port = server_config.getint("listen_port")
        if not listen_port:
            logger.error("listen_port not set, exiting...")
            sys.exit(-1)
    except (ValueError, KeyError) as e:
        logger.debug("invalid listen_port: {e}", e=e, exc_info=True)
        logger.error("invalid listen_port, exiting...")
        sys.exit(-1)

    stop_event = threading.Event()
    addr = ("127.0.0.1", listen_port)
    server = None
    try:
        server = TKLServer(addr, TKLRequestHandler, stop_event=stop_event,
                           discord_config=config["discord"])
        logger.info("serving at: {host}:{port}", host=addr[0], port=addr[1])
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
