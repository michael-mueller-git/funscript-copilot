import logging
import time
import os

import matplotlib.pyplot as plt
import numpy as np

from funscript_toolbox.data.ffmpegstream import FFmpegStream, VideoInfo
from funscript_toolbox.detectors.yolov10 import YOLOv10
from funscript_toolbox.algorithms.ppca import PPCA
from scipy.interpolate import interp1d
from funscript_toolbox.ui.opencvui import OpenCV_GUI, OpenCV_GUI_Parameters
from funscript_toolbox.data.signal import Signal, SignalParameter
from funscript_copilot.ws_com import WS

class CockTracker:
    def __init__(self, args):
        self.args = args
        self.logger = logging.getLogger(__name__)
        self.video_file = args.input
        self.video_info = FFmpegStream.get_video_info(args.input)
        self.frame_time_in_ms = 1000.0 / self.video_info.fps
        self.ui = OpenCV_GUI(OpenCV_GUI_Parameters(
            video_info = self.video_info,
            skip_frames = 0,
            end_frame_number = self.video_info.length
        ))
        self.frame_time_in_ms = 1000.0 / self.video_info.fps
        self.ws = WS(args.port)

    def start(self):
        self.ws.execute(self.generate_actions)

    def generate_actions(self, start_timestamp_in_ms, script_index):
        first_frame = FFmpegStream.get_frame(self.video_file, start_timestamp_in_ms)
        projection_keys = list(self.ui.projection_config.keys())
        idx = self.ui.menu("Video Projection", projection_keys) - 1
        config = self.ui.get_video_projection_config(first_frame, projection_keys[idx], True)

        start_frame = round(start_timestamp_in_ms / self.frame_time_in_ms)
        ffmpeg = FFmpegStream(
            video_path = self.video_file,
            config = config,
            skip_frames = 0,
            start_frame = start_frame 
        ) 

        detector = YOLOv10(os.path.join(os.path.dirname(__file__), "models" "cock_tracker.onnx"), 0.6)

        x, y = [], []
        num = 0
        self.ui.clear_keypress_queue()
        reason = "End of Stream"
        while ffmpeg.isOpen() and not self.ws.stop:
            num += 1
            frame = ffmpeg.read()
            if frame is None:
                reason = "Failed to read next frame"
                self.logger.warning(reason)
                break

            frame, detections = detector.detect(frame)

            if len(detections) > 0:
                detections = sorted(detections, key=lambda x: x['score'], reverse=True)
                x.append(num)
                y.append(detections[0]['box'][3])

            key = self.ui.preview(
                    frame,
                    num + start_frame,
                    texte = ["Press 'q' to stop tracking"],
                    boxes = [],
                )

            if self.ui.was_key_pressed('q') or key == ord('q'):
                reason = "Stopped by user"
                break

        ffmpeg.stop()
        self.ui.show_loading_screen()

        fh  = interp1d(x, y, kind = 'quadratic')
        x2 = [i for i in range(min(x), max(x))]
        y2 = [float(fh(i)) for i in x2]
        
        y2 = Signal.moving_average(y2, 3)

        min_frame = np.argmin(np.array(y2)) + start_frame
        max_frame = np.argmax(np.array(y2)) + start_frame

        imgMin = FFmpegStream.get_frame(self.video_file, min_frame)
        imgMax = FFmpegStream.get_frame(self.video_file, max_frame)

        imgMin = FFmpegStream.get_projection(imgMin, config)
        imgMax = FFmpegStream.get_projection(imgMax, config)

        (desired_min, desired_max) = self.ui.min_max_selector(
            image_min = imgMin,
            image_max = imgMax,
            info = reason,
            title_min = "Minimum",
            title_max = "Maximum"
        )
        
        self.ui.close()

        y2 = Signal.scale(y2, desired_min, desired_max)

        signal = Signal(SignalParameter(
                additional_points_merge_time_threshold_in_ms = 50,
                additional_points_merge_distance_threshold = 8,
                high_second_derivative_points_threshold = 12,
                distance_minimization_threshold = 12,
                local_min_max_filter_len = 3,
                direction_change_filter_len = 3
            ), self.video_info.fps
        )
        
        result_idx = signal.decimate(
            y2,
            Signal.BasePointAlgorithm.local_min_max,
            [],
            1
        )
            
        categorized = signal.categorize_points(y2, result_idx)
        score = y2
        offset_upper = 10
        offset_lower = 10
        score_min, score_max = min(score), max(score)

        for idx in categorized['upper']:
            score[idx] = max(( score_min, min((score_max, score[idx] + offset_upper)) ))

        for idx in categorized['lower']:
            score[idx] = max(( score_min, min((score_max, score[idx] - offset_lower)) ))

        result_score = [val for idx,val in enumerate(score) if idx in result_idx]

        if False:
            plt.plot(x2,y2)
            plt.plot(result_idx, result_score)
            plt.show()

        count = 0
        for idx, val in enumerate(score):
            if idx in result_idx:
                self.ws.queue.put((script_index, (start_timestamp_in_ms + (idx+1)*self.frame_time_in_ms, val)))
                count += 1
                if count % 512 == 0:
                    time.sleep(0.333)


