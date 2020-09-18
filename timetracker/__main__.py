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
import os
import json
import datetime
import argparse
import logging

import psutil

from .models import session, Program, TimeEntry
from . import utils


log = logging.getLogger("timetracker")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


class MainDisplay(tk.Frame):
    """Main display that greets the user upon opening

    This shows stats for today as well as the current activity time
    """

    def __init__(self, master):
        tk.Frame.__init__(self, master)


class Application(tk.Frame):
    """Main application frame"""

    def __init__(self, master, no_gui):
        tk.Frame.__init__(self, master)
        log.info("Initiating Application")

        # check if a data folder exists
        if not os.path.exists("data"):
            log.info("data dir not found, creating")
            os.makedirs("data")

        # TODO: make more things that you can configure (theme for example)
        default_config = {"mouse_timeout": 10}

        # check if a data/config file exists
        if not os.path.isfile("data/config.json"):
            log.info("config file not found, creating")
            with open("data/config.json", "w") as f:
                json.dump(default_config, f, indend=4, sort_keys=True)
                self.config = default_config

        else:
            log.info("Opening config file")
            with open("data/config.json", "r") as f:
                self.config = json.load(f)

        # record mouse movement
        self.active_last = datetime.datetime.utcnow()
        master.bind("<Motion>", self.on_activity)
        master.bind("<KeyPress>", self.on_activity)

        log.info("Loading programs from db")
        self.load_programs()

        log.info("Deleting unfinished time entries")
        TimeEntry.delete_unfinished_entries()
        log.info("Starting activity loop")
        self.activity_loop()

        if not no_gui:
            log.info("Registering MainDisplay")
            self.main_display = MainDisplay(self)
            self.main_display.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    def load_programs(self):
        """Load all the user's programs into memory for tracking"""
        self.programs = session.query(Program)
        self.current_program = None

    def start_logging_program(self, program):
        """Start logging a program to the db"""
        TimeEntry.start_logging(program.id)

    def stop_logging_program(self, program):
        """Stop logging a program to the db"""
        TimeEntry.stop_logging(program.id)

    def activity_loop(self):
        """Main activity loop that does all the program detection

        This loop checks if any of the programs are open, if they are active, and
        whether or not the mouse is active.
        """
        # check immediately if the user is inactive to save on processing time
        time_since = datetime.datetime.utcnow() - self.active_last
        if self.current_program and time_since.seconds > int(
            self.config["mouse_timeout"]
        ):
            log.info(f"It's been {self.config['mouse_timeout']} second since last active, "f"stopping logging program {self.current_program}")
            self.stop_logging_program(self.current_program)
            self.current_program = None

            # just call after here so we don't have to indent again
            self.after(500, self.activity_loop)
            return

        # if the current program isn't set, check if one of the programs
        # is an active window
        # if not self.current_program:
        program_names = {p.process_name: p for p in self.programs}
        processes = utils.get_processes(program_names.keys())

        if processes:
            # loop through processes to see if there's an active one
            active_program = None
            for name, proc in processes:
                if utils.is_active_window(proc.pid):
                    active_program = program_names[name]
                    break

            if self.current_program:
                # if the current program is set but there is no longer
                # an active program, stop logging the current program and
                # set the current program to None
                if not active_program:
                    self.stop_logging_program(self.current_program)
                    self.current_program = None

                # if the current program is set and there's a new active program,
                # stop logging the current program and start logging the new one
                # while setting the current program to the new one
                if self.current_program.id != active_program.id:
                    self.stop_logging_program(self.current_program)
                    self.start_logging_program(active_program)
                    self.current_program = active_program

            else:
                # if there's an active program but no current program set,
                # just start logging the active program and set the current
                # program to the active program
                if active_program:
                    self.start_logging_program(active_program)
                    self.current_program = active_program

        self.after(500, self.activity_loop)

    def on_activity(self, event):
        """Records the last time the user was active (for inactivity tracking)"""
        self.active_last = datetime.datetime.utcnow()


def check_pid():
    """Checks if another instance of the app is running"""
    filename = "instance_lock.txt"

    def write_pid():
        with open(filename, "w") as f:
            f.write(os.getpid())

    if not os.path.isfile(filename):
        write_pid()
        return True

    with open(filename, "r") as f:
        other_pid = int(f.read())

    try:
        proc = psutil.Process(other_pid)
        return proc  # process exists and is running

    except psutil.NoSuchProcess:
        # process existed but is no longer running
        # replace old pid with our new one
        write_pid()
        return True


def main():
    log.info("Starting app")
    other_proc = check_pid()
    if not other_proc:
        # TODO: I need to somehow start the GUI for the running process
        # right now it just ends which isn't great
        log.info("Another instance is running, exiting")
        return

    log.info("Parsing args")
    # parse CLI args
    parser = argparse.ArgumentParser(
        description="Time Tracker: A Windows app written in Python that tracks your time for specified apps"
    )
    parser.add_argument(
        "--no-gui", help="A flag that disables the GUI on start", action="store_true"
    )
    args = parser.parse_args()

    log.info("Setting up Tk")
    # setup and start the tkinter root
    root = tk.Tk()
    root.title("Time Tracker")
    root.resizable(width=False, height=False)
    Application(root, args.no_gui).grid(column=0, row=0)
    if args.no_gui:
        root.withdraw()
    log.info("Starting mainloop")
    root.mainloop()


if __name__ == "__main__":
    main()
