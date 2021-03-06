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

try:
    import sqlalchemy
except ImportError:
    print("Cannot run. Please run 'setup.bat' before continuing.")
    import sys
    sys.exit()


import tkinter as tk
import argparse
import logging
from logging.handlers import RotatingFileHandler
import sys

import utils
from app import Application
import updater


max_bytes = 32 * 1024 * 1024  # 32 MiB
log = logging.getLogger("timetracker")
log.setLevel(logging.INFO)
sh = logging.StreamHandler()
handler = RotatingFileHandler(
    filename="timetracker.log",
    encoding="utf-8",
    mode="w",
    maxBytes=max_bytes,
    backupCount=5,
)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
sh.setFormatter(fmt)
handler.setFormatter(fmt)
log.addHandler(sh)
log.addHandler(handler)


def main():
    log.info("Starting app...")

    other_proc = utils.is_already_running()

    if not other_proc:
        log.info("Instance check passed")

    else:
        log.info("Another instance is running, requesting it to open its GUI...")
        try:
            utils.multiprocess_sender()
            log.info("Sent message. Hopefully it worked? Exiting...")
            return

        except Exception:
            log.info("Message failed to send. Uh oh. Attempting to kill other process...")

            try:
                other_proc.kill()
            except Exception:
                log.info("Failed to kill other process. Writing to lockfile and continuing with startup...")
                utils.write_pid()

            else:
                log.info("Successfully killed other process. Writing to lockfile and continuing with startup...")
                utils.write_pid()

    log.info("Parsing args...")
    # parse CLI args
    parser = argparse.ArgumentParser(
        description="Time Tracker: A Windows app written in Python that tracks your time for specified apps"
    )
    parser.add_argument(
        "--no-gui", help="A flag that disables the GUI on start", action="store_true"
    )
    parser.add_argument(
        "--update", "-U", help="A flag that updates the app", action="store_true"
    )
    args = parser.parse_args()

    log.info("Setting up Tk...")
    # setup and start the tkinter root
    root = tk.Tk()
    root.title("Time Tracker")
    root.iconbitmap("icon.ico")
    root.resizable(width=False, height=False)

    if args.update:
        root.withdraw()
        log.info("Update arg specified, performing update...")
        updater.perform_update(root, restart=False)
        return

    Application(root, args.no_gui).grid(column=0, row=0)

    if args.no_gui:
        root.withdraw()

    log.info("Starting mainloop...")
    root.mainloop()

    log.info("Deleting lockfile...")
    try:
        result = utils.delete_lockfile()
        if not result:
            log.info("Lockfile does not exist, skipping deletion")

    except Exception:
        log.info("Failed to delete lockfile")

    log.info("Exiting...")
    sys.exit()


if __name__ == "__main__":
    main()
