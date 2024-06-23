
import websockets
import json
import logging
import asyncio
import time

from queue import Queue
from threading import Thread


class WS:
    def __init__(self, port):
        self.logger = logging.getLogger(__name__)
        self.port = port
        self.stop = False
        self.should_exit = False        
        self.next_start_in_ms = None
        self.next_script_index = None
        self.queue = Queue(maxsize=2048)

    async def ws_consumer_handler(self, websocket):
        while not self.should_exit:
            msg = await websocket.recv()
            try:
                msg = json.loads(msg)
            except:
                continue

            if any(x not in msg for x in ["name", "data", "type"]):
                continue

            if msg["name"] != "user_data_01":
                continue

            if any(x not in msg["data"] for x in ["message", "source"]):
                continue

            if msg["data"]["source"] != "copilot":
                continue

            if "action" not in msg["data"]["message"]:
                continue

            self.logger.info("ws receive %s", str(msg))

            if msg["data"]["message"]["action"] == "exit":
                self.logger.warning("ws event request exit")
                self.stop = True
                self.should_exit= True

            if msg["data"]["message"]["action"] == "stop":
                self.logger.warning("ws event request stop")
                self.stop = True

            if msg["data"]["message"]["action"] == "start":
                self.logger.info("ws event request start")
                self.next_start_in_ms = msg["data"]["message"]["startPosition"] * 1000.0 \
                        if "startPosition" in msg["data"]["message"] else 0.0
                self.next_script_index = msg["data"]["message"]["scriptIdx"] \
                        if "scriptIdx" in msg["data"]["message"] else None

    async def ws_producer_handler(self, websocket):
        while True:
            if self.queue.qsize() < 1:
                if self.should_exit:
                    return
                else:
                    await asyncio.sleep(0.2)
            else:
                item = self.queue.get()
                msg = {
                    "type": "command",
                    "name": "add_action",
                    "data": {
                        "at": item[1][0] / 1000.0,
                        "pos": int(item[1][1])
                    }
                }

                if item[0] is not None:
                    msg["scriptIndex"] = item[0]

                await websocket.send(json.dumps(msg))

    def run_ws_event_loop(self):
        async def ws_handler():
            ws_url = f'ws://localhost:{self.port}/ofs'
            print("Websocket connect to", ws_url)
            async with websockets.connect(ws_url) as websocket:
                websocket.ping_timeout = 3600*24
                consumer_task = asyncio.ensure_future(self.ws_consumer_handler(websocket))
                producer_task = asyncio.ensure_future(self.ws_producer_handler(websocket))
                _, pending = await asyncio.wait(
                    [consumer_task, producer_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ws_handler())

    def execute(self, callback):
        self.logger.info("Start Copilot WS")
        ws_thread = Thread(target = self.run_ws_event_loop)
        ws_thread.start()

        while not self.should_exit:
            if self.next_start_in_ms is None:
                time.sleep(0.2)
            else:
                script_index, start_timestamp_in_ms = self.next_script_index, self.next_start_in_ms
                self.next_script_index, self.next_start_in_ms = None, None
                callback(start_timestamp_in_ms, script_index)
