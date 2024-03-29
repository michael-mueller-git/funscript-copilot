import setuptools
import os
import glob
import sys

# THIS IS ONLY A DUMMY SETUP.PY!!

PACKAGE = 'funscript_copilot'
DESCRIPTION = "A tool to create funscripts"
VERSION = "0.0.0"

setuptools.setup(
    name=PACKAGE.replace('_', '-'),
    version=VERSION.replace('v', ''),
    author="btw i use arch",
    author_email="git@local",
    description=DESCRIPTION,
    long_description=long_description,
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
    install_requires=requirements,
    packages=[PACKAGE],
    package_data={PACKAGE: src},
    data_files=[(os.path.join('/', PACKAGE, os.path.dirname(x)), [x]) for x in docs],
    python_requires=">=3.6",
    setup_requires=['wheel'],
)
