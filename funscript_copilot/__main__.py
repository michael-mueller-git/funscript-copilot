import argparse
import os
import sys

from funscript_copilot.motion_analyser import MotionAnalyser

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib"))

def entrypoint():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type = str, help = "Video File")
    args = parser.parse_args()

    motion_analyser = MotionAnalyser(args)
    motion_analyser.start()

