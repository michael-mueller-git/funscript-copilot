import setuptools
import os
import glob
import sys
import git # pip install gitpython

# THIS IS ONLY A DUMMY SETUP.PY!!

PACKAGE = 'funscript_copilot'
DESCRIPTION = "A tool to create funscripts"
VERSION = "0.0.0"

try:
    src = [os.path.join('..', x) \
                for x in git.Git('.').ls_files().splitlines() \
                if x.startswith(PACKAGE+os.sep) or x.startswith("lib") \
                and os.path.exists(x)]
except:
    print("Warning fallback to glob")
    src = [os.path.join('..', f) for f in glob.glob(PACKAGE+os.sep+"**"+os.sep+"*", recursive=True)]
    src += [os.path.join('..', f) for f in glob.glob("lib"+os.sep+"**"+os.sep+"*", recursive=True)]

setuptools.setup(
    name=PACKAGE.replace('_', '-'),
    version=VERSION.replace('v', ''),
    author="btw i use arch",
    author_email="git@local",
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            str(PACKAGE.replace('_', '-') + '=' + PACKAGE + '.__main__:main'),
        ]
    },
    install_requires=[],
    packages=[PACKAGE],
    package_data={PACKAGE: src},
    data_files=[],
    python_requires=">=3.6",
    setup_requires=['wheel'],
)
