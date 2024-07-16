import argparse
import os
import sys
import logging
import platform

from funscript_copilot.optical_flow import MotionAnalyser
from funscript_copilot.cock_tracker import CockTracker

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib"))

def setup_logging():
    logging.basicConfig(
        level=os.getenv('LOG_LEVEL', "INFO"),
        format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(stream=sys.stdout)
        ]
    )

def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type = str, help = "Video File")
    parser.add_argument("-p", "--port", type = int, default = 8080, help = "Websocket Port")
    subparsers = parser.add_subparsers(dest='method')
    _ = subparsers.add_parser('dense-optical-flow', help='generate funscript actions by using dense optical flow')
    cockTrackerArgs = subparsers.add_parser('cock-tracker', help='generate funscript actions by using yolov10 detector')
    cockTrackerArgs.add_argument("-i", "--classId", type = int, default = 0, help = "cock class id")
    cockTrackerArgs.add_argument("-m", "--model", type = str, default = None, help = "path to yolov10 onnx")
    cockTrackerArgs.add_argument("-c", "--confidence", type = float, default = 0.5, help = "detection confidence threshold")
    cockTrackerArgs.add_argument('--test', help='test mode', action='store_true')
    args = parser.parse_args()

    setup_logging()

    if not os.path.exists(args.input):
        raise FileNotFoundError(args.input)

    if platform.system().lower().startswith("linux") or os.path.abspath(__file__).startswith("/nix"):
        # pynput does not work well with native wayland so we use xwayland to get proper keyboard inputs
        if os.environ.get('DISPLAY'):
            print("Warning: Force QT_QPA_PLATFORM=xcb for better user experience")
            os.environ['QT_QPA_PLATFORM'] = "xcb"

    match args.method: 
        case 'dense-optical-flow':
            motion_analyser = MotionAnalyser(args)
            motion_analyser.start()
        case 'cock-tracker':
            tracker = CockTracker(args)
            tracker.start()
        case _:
            raise NotImplementedError(f"{args.method} is not available")

def main():
    """ CLI Main Function """
    entrypoint()
