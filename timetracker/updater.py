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
import sys
import subprocess
import urllib.request
import collections
import logging
import time

from widgets import YesNoPrompt


log = logging.getLogger("timetracker.updater")


VersionInfo = collections.namedtuple("VersionInfo", "major minor micro releaselevel serial")


def check_for_updates():
    """Request the latest release from GitHub and check it with the current version"""
    try:
        with urllib.request.urlopen("https://api.github.com/repos/Fyssion/TimeTracker/tags") as response:
            raw = response.read()

        tags = json.loads(raw)

    except Exception:
        return False

    if not tags:
        return False

    # remove v from ex: v0.2.0
    version = tags[0]["name"].strip("v")

    if version.endswith("a"):
        releaselevel = "alpha"

    else:
        releaselevel = "final"

    numbers = version.split(".")
    version = [int(n) for n in numbers]
    version.append(releaselevel)
    version.append(0)

    other_version = VersionInfo(*version)

    from __init__ import version_info as my_version

    if other_version > my_version:
        return True

    else:
        return False


def pull_from_github():
    """Get the lastest changes from GitHub"""
    # Make sure that we're in a Git repository
    if not os.path.isdir(".git"):
        raise EnvironmentError("This isn't a Git repository.")

    # Make sure that we can actually use Git on the command line
    # because some people install Git Bash without allowing access to Windows CMD
    try:
        subprocess.check_call("git --version", shell=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        raise EnvironmentError(
            "Couldn't use Git on the CLI. You will need to run 'git pull' yourself."
        )

    print("Passed Git checks...")

    # Check that the current working directory is clean
    sp = subprocess.check_output(
        "git status --porcelain", shell=True, universal_newlines=True
    )
    if sp:
        raise EnvironmentError("Oh no! There are modified files in this repo. Skipping git pull.")

    print("Pulling from GitHub...")

    try:
        subprocess.check_call("git pull", shell=True)
    except subprocess.CalledProcessError:
        raise OSError(
            "Could not update the app. You will need to run 'git pull' yourself."
        )


def restart_app():
    """This will restart the app"""
    os.execv(sys.argv[0], sys.argv)
    sys.exit()


def perform_update(root, restart=True):
    """Perform the full update process

    This includes checking for updates, asking the user for confirmation,
    pulling from GitHub, and restarting the app.
    """
    log.info("Checking for updates...")
    if not check_for_updates():
        return

    log.info("Prompting user about update...")
    prompt = YesNoPrompt(root, "A new update is available for TimeTracker. Update?")
    root.wait_window(prompt)

    if not prompt.result:
        log.info("User doesn't want update, aborting...")
        return

    log.info("Pulling from GitHub...")

    try:
        pull_from_github()
    except Exception as e:
        log.exception(str(e))
        return

    log.info("Done!")

    if restart:
        log.info("Restarting app...")
        restart_app()
