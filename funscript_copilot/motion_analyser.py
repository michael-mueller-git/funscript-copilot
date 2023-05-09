import asyncio
import logging
import websockets
import json
import os
import cv2

import numpy as np
import matplotlib.pyplot as plt

from enum import Enum
from sklearn.decomposition import IncrementalPCA


class EMA:

    def __init__(self, alpha = 0.05):
        self.alpha = alpha
        self.mean = 0

    def update(self, val: float) -> float:
        self.mean = ((1.0 - self.alpha) * self.mean) + (self.alpha * val)
        return self.mean


class Turnpoints:

    class Action(Enum):
        Top = 1
        Bottom = 2

    def __init__(self, fps):
        self.fps = fps
        self.top = []
        self.bottom = []
        self.trace = []
        self.prev_turnpoint = None
        self.idx = 0

    def update(self, val):
        self.idx += 1
        if self.prev_turnpoint is None:
            self.prev_turnpoint = Turnpoints.Action.Top if val < 0.0 else Turnpoints.Action.Bottom
            return

        if self.prev_turnpoint == Turnpoints.Action.Top:
            if val < 0.0:
                self.bottom.append(self.idx)
                self.trace.append((self.idx, Turnpoints.Action.Bottom))
                self.prev_turnpoint = Turnpoints.Action.Bottom
        elif self.prev_turnpoint == Turnpoints.Action.Bottom:
            if val > 0.0:
                self.top.append(self.idx)
                self.trace.append((self.idx, Turnpoints.Action.Top))
                self.prev_turnpoint = Turnpoints.Action.Top


    def get_turnpoints_with_ms_pos(self):
        frame_time = 1000.0 / self.fps
        return {
            'top': [x * frame_time for x in self.top],
            'bottom': [x * frame_time for x in self.bottom]
        }


    def get_turnpoints_with_idx_pos(self):
        return {
            'top': self.top,
            'bottom': self.bottom
        }


    def get_signal(self, bottom_val = 0, top_val = 100) -> tuple:
        return ([x[0] for x in self.trace], [bottom_val if x[1] == Turnpoints.Action.Bottom else top_val for x in self.trace])




class MotionAnalyser:

    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.should_exit = False
        self.video_file = args.input
        self.video = cv2.VideoCapture(args.input)
        self.fps = self.video.get(cv2.CAP_PROP_FPS)
        self.n_components = 2
        self.stop = False
        self.batch_size = int(self.fps * 1.2)
        self.ipca = IncrementalPCA(n_components=self.n_components, batch_size=self.batch_size)
        self.load_gt()


    def load_gt(self):
        self.gt_funscript_path = '.'.join(self.video_file.split('.')[:-1]) + ".funscript"
        if not os.path.exists(self.gt_funscript_path):
            self.logger.info("ground truth funscript %s not exists", self.gt_funscript_path)
            self.gt_actions = {'x':[], 'y':[]}
            return

        self.logger.info("load gt funscript %s", self.gt_funscript_path)
        with open(self.gt_funscript_path, "r") as f:
            self.gt_funscript = json.load(f)

        frame_time = 1000.0 / self.fps

        self.gt_actions = {
            'x': [action["at"]/frame_time for action in self.gt_funscript["actions"]],
            'y': [action["pos"] for action in self.gt_funscript["actions"]]
        }


    async def ws_event_loop(self):
        async with websockets.connect('ws://localhost:8080/ofs') as websocket:
            welcome_msg = await websocket.recv()
            print(welcome_msg)
            while not self.should_exit:
                await asyncio.sleep(1)

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
        frame = cv2.resize(frame, None, fx=0.1, fy=0.1)
        height, width = frame.shape[:2]
        if 2*height == width:
            # vr frame
            frame = frame[:, :int(width/2)]
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    def start(self):
        self.logger.info("Start MotionAnalyser")
        # asyncio.get_event_loop().run_until_complete(self.ws_event_loop())

        frame_number = 0
        prev_frame = None
        y_batch = []
        all_data = []
        prediction_pca = [[] for _ in range(self.n_components)]
        turnpoints =  Turnpoints(self.fps)
        while self.video.isOpened() and not self.stop:
            frame_number += 1
            self.logger.debug(f"Process frame {frame_number}")
            success, frame = self.video.read()
            if not success:
                self.logger.warning("Failed to read next frame")
                break

            frame = self.get_low_rank_adoption(frame)
            if prev_frame is None:
                prev_frame = frame
                continue

            flow = cv2.calcOpticalFlowFarneback(prev_frame, frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            prev_frame= frame
            y_batch.append(np.array(flow[..., 1]).flatten())
            all_data.append(np.array(flow[..., 1]).flatten())

            if len(y_batch) >= self.batch_size:
                self.ipca.partial_fit(y_batch)
                batch_prediction_pca = np.transpose(np.array(self.ipca.transform(y_batch)))
                _, _, batch_prediction_svd = np.linalg.svd(np.transpose(np.array(y_batch)), full_matrices=False)
                batch_prediction_svd = np.array(batch_prediction_svd[:self.n_components,:])
                y_batch = []
                for i in range(self.n_components):
                    prediction_pca[i].extend(batch_prediction_pca[i])

                if self.n_components == 2:
                    relative_movement = np.array(batch_prediction_pca[0]) + np.array(batch_prediction_pca[1])
                    for item in relative_movement:
                        turnpoints.update(item)


        self.video.release()

        if self.n_components == 2:
            x, y = turnpoints.get_signal()
            plt.plot(x, y)
            plt.plot(self.gt_actions['x'], MotionAnalyser.scale(self.gt_actions['y'], 0, 100))
        else:
            for i in range(self.n_components):
                plt.plot(prediction_pca[i])

        plt.show()

        self.should_exit = True



