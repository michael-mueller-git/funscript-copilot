import argparse
import os
import sys
import logging

from funscript_copilot.motion_analyser import MotionAnalyser

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
    parser.add_argument("-i", "--input", type = str, help = "Video File")
    args = parser.parse_args()

    setup_logging()

    if args.input is None:
        print("ERROR: Missing Video File Parameter")
        sys.exit()

    if not os.path.exists(args.input):
        raise FileNotFoundError(args.input)

    motion_analyser = MotionAnalyser(args)
    motion_analyser.start()

def main():
    """ CLI Main Function """
    entrypoint()
