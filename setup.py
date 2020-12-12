"""
MIT License

Copyright (c) 2020 Fyssion

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import os
import json
import subprocess
import sys
import enum


class UpdateResponse(enum.Enum):
    SUCCESS = 0
    DEPS_FAILED = 1
    GIT_PULL_FAILED = 2


def update_deps():
    """Update the deps with pip"""
    print("Attempting to update dependencies...")

    try:
        subprocess.check_call(
            f'"{sys.executable}" -m pip install --no-warn-script-location --user -U -r requirements.txt',
            shell=True,
        )
    except subprocess.CalledProcessError:
        raise OSError(
            "Could not update dependencies. "
            f"You will need to run '\"{sys.executable}\" -m pip install -U -r requirements.txt' yourself."
        )


def initial_setup():
    """Run the initial setup for the app

    This installs the deps and makes the config files/dirs"""
    try:
        update_deps()
    except OSError as e:
        print(str(e))
        return UpdateResponse.DEPS_FAILED

    # check if a data folder exists
    if not os.path.exists("data"):
        print("data dir not found, creating...")
        os.makedir("data")

    # TODO: make more things that you can configure (theme for example)
    default_config = {"mouse_timeout": 10}

    # check if a data/config file exists
    if not os.path.isfile("data/config.json"):
        print("config file not found, creating...")
        with open("data/config.json", "w") as f:
            json.dump(default_config, f, indent=4, sort_keys=True)

    # TODO: add program to start menu and startup programs

    print("Done! You may now run the program.")


if __name__ == "__main__":
    initial_setup()
