import logging
import cv2

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from funscript_toolbox.data.ffmpegstream import FFmpegStream, VideoInfo
from funscript_toolbox.detectors.yolov10 import YOLOv10
from funscript_toolbox.algorithms.ppca import PPCA
from scipy.interpolate import interp1d


class AutoTracker:
    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.should_exit = False
        self.port = args.port
        self.stop = False
        self.preview = True
        self.video_file = args.input
        self.video_info = FFmpegStream.get_video_info(args.input)
        self.frame_time_in_ms = 1000.0 / self.video_info.fps


    def start(self, start_timestamp_in_ms = 0):
        ffmpeg = FFmpegStream(
            video_path = self.video_file,
            config = { "video_filter": "v360=input=he:in_stereo=sbs:pitch=${pitch}:yaw=${yaw}:roll=${roll}:output=flat:d_fov=${fov}:w=${width}:h=${height}",
                "parameter": {
                    "width": 640,
                    "height": 640,
                    "fov": 90,
                    "pitch": -40,
                    "yaw": 0,
                    "roll": 0
                }
            },
            skip_frames = 0,
            start_frame = round(start_timestamp_in_ms / self.frame_time_in_ms)
        ) 

        detector = YOLOv10(0.6)

        x, y = [], []
        num = 0
        while ffmpeg.isOpen() and not self.stop:
            num += 1
            frame = ffmpeg.read()
            if frame is None:
                self.logger.warning("Failed to read next frame")
                break

            frame, detections = detector.detect(frame)

            if len(detections) > 0:
                detections = sorted(detections, key=lambda x: x['score'], reverse=True)
                x.append(num)
                y.append(detections[0]['box'][3])

            if self.preview:
                cv2.imshow("preview", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        cv2.destroyAllWindows()
        ffmpeg.stop()

        fh  = interp1d(x, y, kind = 'quadratic')
        x2 = [x for x in range(min(x), max(x))]
        y2 = [float(fh(x)) for x in x2]
        
        w = 3
        avg = np.convolve(y2, np.ones(int(w*2)) / (w*2), 'valid')
        y2 = [sum(y2[:i*2]) / (i*2) for i in range(1, w+1)]+list(avg)+[sum(y2[-i*2:]) / (i*2) for i in range(w, 1, -1)]

        plt.plot(x,y)
        plt.plot(x2,y2)
        plt.show()


