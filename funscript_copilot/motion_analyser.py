import asyncio
import logging
import websockets
import json
import os
import time
import cv2
import sys

import numpy as np
import matplotlib.pyplot as plt

from queue import Queue
from threading import Thread
from enum import Enum
from sklearn.decomposition import IncrementalPCA

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib"))

from funscript_toolbox.data.ffmpegstream import FFmpegStream, VideoInfo


class Turnpoints:

    class Action(Enum):
        Top = 1
        Bottom = 2

    def __init__(self, fps, bottom_val = 0, top_val = 100):
        self.fps = fps
        self.frame_time = 1000.0 / self.fps
        self.bottom_val = bottom_val
        self.top_val = top_val
        self.top = []
        self.bottom = []
        self.trace = []
        self.prev_turnpoint = None
        self.idx = 0

    def update(self, val):
        self.idx += 1
        if self.prev_turnpoint is None:
            self.prev_turnpoint = Turnpoints.Action.Top if val < 0.0 else Turnpoints.Action.Bottom
            return None

        if self.prev_turnpoint == Turnpoints.Action.Top:
            if val < 0.0:
                self.bottom.append(self.idx)
                self.trace.append((self.idx, Turnpoints.Action.Bottom))
                self.prev_turnpoint = Turnpoints.Action.Bottom
                return (self.idx*self.frame_time, self.bottom_val)
        elif self.prev_turnpoint == Turnpoints.Action.Bottom:
            if val > 0.0:
                self.top.append(self.idx)
                self.trace.append((self.idx, Turnpoints.Action.Top))
                self.prev_turnpoint = Turnpoints.Action.Top
                return (self.idx*self.frame_time, self.top_val)

        return None




class MotionAnalyser:

    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.should_exit = False
        self.video_file = args.input
        self.video_info = FFmpegStream.get_video_info(args.input)
        scale = self.video_info.width // 256
        self.ffmpeg = FFmpegStream(args.input, {
            "video_filter": "scale=${width}:${height}",
            "parameter": {
                "width": self.video_info.width//scale,
                "height": self.video_info.height//scale
            }
        })
        self.n_components = 2
        self.stop = False
        self.batch_size = int(self.video_info.fps * 1.2)
        self.ipca = IncrementalPCA(n_components=self.n_components, batch_size=self.batch_size)
        self.queue = Queue(maxsize=1024)


    async def ws_event_loop(self):
        try:
            async with websockets.connect('ws://localhost:8080/ofs') as websocket:
                welcome_msg = await websocket.recv()
                print(welcome_msg)
                while not self.should_exit:
                    if self.queue.qsize() < 1:
                        await asyncio.sleep(0.2)
                    else:
                        item = self.queue.get()
                        await websocket.send(json.dumps({
                                "type": "command",
                                "name": "add_action",
                                "data": {
                                    "at": item[0] / 1000.0,
                                    "pos": int(item[1])
                                }
                            }))
        except:
            self.logger.warning("ws crashed")

    @staticmethod
    def scale(signal: list, lower: float = 0, upper: float = 99) -> list:
        """ Scale an signal (list of float or int) between given lower and upper value

        Args:
            signal (list): list with float or int signal values to scale
            lower (float): lower scale value
            upper (float): upper scale value

        Returns:
            list: list with scaled signal
        """
        if len(signal) == 0:
            return signal

        if len(signal) == 1:
            return [lower]

        signal_min = min(signal)
        signal_max = max(signal)
        return [(float(upper) - float(lower)) * (x - signal_min) / (signal_max - signal_min) + float(lower) for x in signal]


    def get_low_rank_adoption(self, frame) -> np.ndarray:
        height, width = frame.shape[:2]
        if 2*height == width:
            # vr frame
            frame = frame[:, :int(width/2)]
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    def run_ws_event_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.ws_event_loop())

    def start(self):
        self.logger.info("Start MotionAnalyser")
        ws_thread = Thread(target = self.run_ws_event_loop)
        ws_thread.start()

        frame_number = 0
        prev_frame = None
        y_batch = []
        # prediction_pca = [[] for _ in range(self.n_components)]
        turnpoints =  Turnpoints(self.video_info.fps)
        start_time = time.time()
        while self.ffmpeg.isOpen() and not self.stop:
            frame_number += 1
            frame = self.ffmpeg.read()
            if frame is None:
                self.logger.warning("Failed to read next frame")
                break

            frame = self.get_low_rank_adoption(frame)
            if prev_frame is None:
                prev_frame = frame
                continue

            if frame_number % 100 == 0:
                self.logger.info("process frame %d", frame_number)

            flow = cv2.calcOpticalFlowFarneback(prev_frame, frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            prev_frame= frame
            y_batch.append(np.array(flow[..., 1]).flatten())

            if len(y_batch) >= self.batch_size:
                self.ipca.partial_fit(y_batch)
                ipca_out = self.ipca.transform(y_batch)
                batch_prediction_pca = np.transpose(np.array(ipca_out))
                y_batch = []
                # for i in range(self.n_components):
                    # prediction_pca[i].extend(batch_prediction_pca[i])

                relative_movement = np.array(batch_prediction_pca[0]) + np.array(batch_prediction_pca[1])
                for item in relative_movement:
                    action = turnpoints.update(item)
                    if action is not None:
                        if not self.queue.full():
                            self.queue.put(action)


        self.ffmpeg.stop()
        self.logger.info("%d sps", int(frame_number / (time.time() - start_time)))

        self.should_exit = True


