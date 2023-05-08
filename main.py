#!/bin/env python3
import multiprocessing
from funscript_copilot.__main__ import entrypoint

if __name__ == "__main__":
    multiprocessing.freeze_support()
    entrypoint()
