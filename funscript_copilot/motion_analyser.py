import asyncio
import logging
import websockets
import json
import cv2

import numpy as np
import matplotlib.pyplot as plt

from sklearn.decomposition import IncrementalPCA


class MotionAnalyser:

    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.should_exit = False
        self.video = cv2.VideoCapture(args.input)
        self.fps = self.video.get(cv2.CAP_PROP_FPS)
        self.n_components = 2
        self.stop = False
        self.batch_size = int(self.fps * 1.2)
        self.ipca = IncrementalPCA(n_components=self.n_components, batch_size=self.batch_size)


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
        prediction_pca = [[] for _ in range(self.n_components)]
        prediction_svd = [[] for _ in range(self.n_components)]
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

            if len(y_batch) >= self.batch_size:
                self.ipca.partial_fit(y_batch)
                batch_prediction_pca = np.transpose(np.array(self.ipca.transform(y_batch)))
                _, _, batch_prediction_svd = np.linalg.svd(np.transpose(np.array(y_batch)), full_matrices=False)
                batch_prediction_svd = np.transpose(np.array(batch_prediction_svd[:self.n_components,:]))
                y_batch = []
                for i in range(self.n_components):
                    prediction_pca[i].extend(batch_prediction_pca[i])
                    prediction_svd[i].extend(batch_prediction_svd[:,i])

        self.video.release()

        if self.n_components == 2:
            result_pca = np.array(prediction_pca[0]) + np.array(prediction_pca[1])
            result_svd = np.array(prediction_svd[0]) + np.array(prediction_svd[1])
            plt.plot(MotionAnalyser.scale(result_pca, -100, 100))
            plt.plot(MotionAnalyser.scale(result_svd, -100, 100))
        else:
            for i in range(self.n_components):
                plt.plot(prediction_pca[i])

        plt.show()

        self.should_exit = True



