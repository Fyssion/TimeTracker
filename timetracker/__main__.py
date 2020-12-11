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


import tkinter as tk
import argparse
import logging
import sys


from app import Application
import utils


log = logging.getLogger("timetracker")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(fmt)
log.addHandler(handler)


def main():
    log.info("Starting app...")

    other_proc = utils.check_pid()
    if other_proc:
        log.info("Another instance is running, requesting it to open its GUI...")
        try:
            utils.multiprocess_sender()

        except Exception:
            log.info("Message failed to send. Uh oh. Exiting anyways...")

        else:
            log.info("Sent message. Hopefully it worked? Exiting...")

        return

    log.info("Parsing args...")
    # parse CLI args
    parser = argparse.ArgumentParser(
        description="Time Tracker: A Windows app written in Python that tracks your time for specified apps"
    )
    parser.add_argument(
        "--no-gui", help="A flag that disables the GUI on start", action="store_true"
    )
    args = parser.parse_args()

    log.info("Setting up Tk...")
    # setup and start the tkinter root
    root = tk.Tk()
    root.title("Time Tracker")
    root.iconbitmap("icon.ico")
    root.resizable(width=False, height=False)

    Application(root, args.no_gui).grid(column=0, row=0)

    if args.no_gui:
        root.withdraw()

    log.info("Starting mainloop...")
    root.mainloop()

    log.info("Exiting...")
    sys.exit()


if __name__ == "__main__":
    main()
