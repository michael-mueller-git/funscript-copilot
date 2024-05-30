import argparse
import os
import sys
import logging

from funscript_copilot.optical_flow import MotionAnalyser
from funscript_copilot.auto_tracker import AutoTracker

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
    _ = subparsers.add_parser('auto-tracker', help='generate funscript actions by using nudenet + ocsort')
    args = parser.parse_args()

    setup_logging()

    if not os.path.exists(args.input):
        raise FileNotFoundError(args.input)

    match args.method: 
        case 'dense-optical-flow':
            motion_analyser = MotionAnalyser(args)
            motion_analyser.start()
        case 'auto-tracker':
            tracker = AutoTracker(args)
            tracker.start()
        case _:
            raise NotImplementedError(f"{args.method} is not available")

def main():
    """ CLI Main Function """
    entrypoint()
