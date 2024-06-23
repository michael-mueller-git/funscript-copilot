import logging
import cv2

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from funscript_toolbox.data.ffmpegstream import FFmpegStream, VideoInfo
from funscript_toolbox.detectors.nudenet import NudeDetector
from funscript_toolbox.detectors.yolov10 import YOLOv10
from funscript_toolbox.trackers.ocsort.ocsort import OCSort
from funscript_toolbox.algorithms.ppca import PPCA

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
        # detector = NudeDetector()
        tracker = OCSort(det_thresh=0.60, max_age=0, min_hits=7)
        y = {}
        
        first = True
        num = 0
        while ffmpeg.isOpen() and not self.stop:
            num += 1
            frame = ffmpeg.read()
            if frame is None:
                self.logger.warning("Failed to read next frame")
                break

            h, w = frame.shape[:2]
            _, detections = detector.detect(frame)
            print(detections)

            if len(detections) == 0:
                continue

            # detections = [d for d in detections if d["class"] in KEEP]
            # print(detections)
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

                    if track_id in y:
                        y[track_id]['y'].append(y1+(y2-y1)/2)
                        y[track_id]['t'].append(num)
                    else:
                        y[track_id] = {
                            'y': [y1+(y2-y1)/2],
                            't': [num]
                        }

                cv2.imshow("preview", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        cv2.destroyAllWindows()
        ffmpeg.stop()

        diff = {}
        for k in y:
            if len(y[k]['t']) > 2:
                diff[k] = {
                    'd': np.diff(y[k]['y'], 1).tolist(),
                    't': y[k]['t'][1:]
                }

        # TODO when handle same id returns later and has nones in between
        arr = []
        for k in diff:
            # print(k , diff[k])
            arr.append([None for _ in range(diff[k]['t'][0])] + diff[k]['d'] + [None for _ in range(num-diff[k]['t'][-1])])

        arr = np.transpose(np.array(arr, dtype=float))
        # print(arr)

        df = pd.DataFrame(arr)
        cov = df.cov()
        x = pd.DataFrame(cov.values[~np.eye(cov.shape[0],dtype=bool)])
        max_idx = x.idxmax(skipna=True)
        column = int(max_idx) // int(cov.shape[0])
        row = int(max_idx) % int(cov.shape[0]) + 1 + column
        print(cov)
        print("found", column, row)

        #print(arr)
        #_, _, _, principalComponents, _ = PPCA(arr, d=1)
        #print(principalComponents.tolist())
        #merged = [item[0] for item in principalComponents.tolist()]
#
        #plt.plot([item[0] for item in principalComponents.tolist()])
        # plt.plot([item[1] for item in principalComponents.tolist()])



        # for k in y:
            #plt.plot(y[k]['t'], y[k]['y'])
            # plt.plot(y[k]['t'][1:], np.diff(y[k]['y'], 1).tolist())
            #x = PPCA(2)
            # _, _, _, principalComponents, _ = PPCA(np.transpose(np.array([self.result[k] for k in self.result.keys()], dtype=float)), d=1)
            # merged = [item[0] for item in principalComponents.tolist()]

        #plt.show()
