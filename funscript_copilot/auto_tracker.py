import logging
import cv2

import numpy as np

from funscript_toolbox.data.ffmpegstream import FFmpegStream, VideoInfo
from funscript_toolbox.detectors.nudenet import NudeDetector
from funscript_toolbox.trackers.ocsort.ocsort import OCSort

KEEP = [
    "FEMALE_GENITALIA_COVERED",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "BELLY_COVERED",
    "ARMPITS_COVERED",
    "ARMPITS_EXPOSED",
    "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
]

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
                    "width": 512,
                    "height": 512,
                    "fov": 120,
                    "pitch": -10,
                    "yaw": 0,
                    "roll": 0
                }
            },
            skip_frames = 0,
            start_frame = round(start_timestamp_in_ms / self.frame_time_in_ms)
        ) 

        detector = NudeDetector()
        tracker = OCSort(det_thresh=0.30, max_age=10, min_hits=2)

        while ffmpeg.isOpen() and not self.stop:
            frame = ffmpeg.read()
            if frame is None:
                self.logger.warning("Failed to read next frame")
                break

            h, w = frame.shape[:2]
            detections = detector.detect(frame)
            detections = [d for d in detections if d["class"] in KEEP]
            print(detections)
            xyxyc = np.array([[d['box'][0], d['box'][1], d['box'][0]+d['box'][2], d['box'][1]+d['box'][3], d['score']] for d in detections])
            _ = tracker.update(xyxyc, (h, w), (h, w))

            if self.preview:
                for track in tracker.trackers:
                    track_id = track.id
                    hits = track.hits
                    x1,y1,x2,y2 = np.round(track.get_state()).astype(int).squeeze()

                    cv2.rectangle(frame, (x1,y1),(x2,y2), (255,0,0), 2)
                    cv2.putText(frame, 
                      f"{track_id}-{hits}", 
                      (x1+10,y1-5), 
                      cv2.FONT_HERSHEY_SIMPLEX, 
                      0.5,
                      (255,0,0), 
                      1,
                      2)

                cv2.imshow("preview", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        cv2.destroyAllWindows()
        ffmpeg.stop()

