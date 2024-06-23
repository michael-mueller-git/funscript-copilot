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
from funscript_copilot.ws_com import WS


class Turnpoints:

    class Action(Enum):
        Top = 1
        Bottom = 2

    def __init__(self, fps, start_offset_in_ms, bottom_val = 0, top_val = 100):
        self.logger = logging.getLogger(__name__)
        self.fps = fps
        self.start_offset_in_ms = start_offset_in_ms
        self.logger.info("use start offfset %d ms", round(self.start_offset_in_ms))
        self.frame_time_in_ms = 1000.0 / self.fps
        self.bottom_val = bottom_val
        self.top_val = top_val
        self.prev_turnpoint = None
        self.idx = 1 # start frame not included

    def update(self, val):
        self.idx += 1
        if self.prev_turnpoint is None:
            self.prev_turnpoint = Turnpoints.Action.Top if val > 0.0 else Turnpoints.Action.Bottom
            return None

        if self.prev_turnpoint == Turnpoints.Action.Top:
            if val < 0.0:
                self.prev_turnpoint = Turnpoints.Action.Bottom
                return (self.idx*self.frame_time_in_ms + self.start_offset_in_ms, self.bottom_val)
        elif self.prev_turnpoint == Turnpoints.Action.Bottom:
            if val > 0.0:
                self.prev_turnpoint = Turnpoints.Action.Top
                return (self.idx*self.frame_time_in_ms + self.start_offset_in_ms, self.top_val)

        return None


class MotionAnalyser:

    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.should_exit = False
        self.video_file = args.input
        self.video_info = FFmpegStream.get_video_info(args.input)
        self.frame_time_in_ms = 1000.0 / self.video_info.fps
        self.n_components = 2
        self.batch_size = int(self.video_info.fps * 1.1)
        self.ipca = IncrementalPCA(n_components=self.n_components, batch_size=self.batch_size)
        self.ws = WS(args.port)

    def get_relevant_data_from_frame(self, frame) -> np.ndarray:
        height, width = frame.shape[:2]
        if 2*height == width:
            # vr frame
            frame = frame[:, :int(width/2)]
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def start(self):
        self.ws.execute(self.generate_actions)

    def generate_actions(self, start_timestamp_in_ms: float, script_index: int):
        self.logger.info("Start MotionAnalyser @ %d ms", round(start_timestamp_in_ms))
        scale = self.video_info.width // 256
        ffmpeg = FFmpegStream(
            video_path = self.video_file,
            config = { "video_filter": "scale=${width}:${height}",
                "parameter": {
                    "width": self.video_info.width//scale,
                    "height": self.video_info.height//scale
                }
            },
            skip_frames = 0,
            start_frame = round(start_timestamp_in_ms / self.frame_time_in_ms)
        )

        sample_counter = 0
        prev_frame = None
        y_batch = []
        turnpoints =  Turnpoints(self.video_info.fps, start_timestamp_in_ms)
        start_time = time.time()
        while ffmpeg.isOpen() and not self.ws.stop:
            sample_counter += 1
            frame = ffmpeg.read()
            if frame is None:
                self.logger.warning("Failed to read next frame")
                break

            frame = self.get_relevant_data_from_frame(frame)
            if prev_frame is None:
                prev_frame = frame
                continue

            flow = cv2.calcOpticalFlowFarneback(prev_frame, frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            prev_frame= frame
            y_batch.append(np.array(flow[..., 1]).flatten())

            if len(y_batch) >= self.batch_size:
                # TODO hangs here in newer nix pkgs
                self.ipca.partial_fit(y_batch)
                ipca_out = self.ipca.transform(y_batch)
                batch_prediction_pca = np.transpose(np.array(ipca_out))
                y_batch = []
                relative_movement = np.array(batch_prediction_pca[0]) - np.array(batch_prediction_pca[1])
                for item in relative_movement:
                    action = turnpoints.update(item)
                    if action is not None:
                        if not self.ws.queue.full():
                            self.ws.queue.put((script_index, action))

        ffmpeg.stop()
        self.logger.info("stop after %d samples (%d SPS)", sample_counter, int(sample_counter / (time.time() - start_time)))
