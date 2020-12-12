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
import time
import threading
import queue
import logging
import functools

from widgets import MainDisplay
from models import session, Program, TimeEntry
import utils
import updater

log = logging.getLogger("timetracker.app")


class Application(tk.Frame):
    """Main application frame"""

    def __init__(self, master, no_gui):
        tk.Frame.__init__(self, master)
        log.info("Initiating Application...")

        master.protocol("WM_DELETE_WINDOW", self.destroy_gui)

        # check if a data folder exists
        if not os.path.exists("data"):
            log.info("data dir not found, creating...")
            os.mkdir("data")

        # TODO: make more things that you can configure (theme for example)
        default_config = {"mouse_timeout": 10}

        # check if a data/config file exists
        if not os.path.isfile("data/config.json"):
            log.info("config file not found, creating...")
            with open("data/config.json", "w") as f:
                json.dump(default_config, f, indent=4, sort_keys=True)
                self.config = default_config

        else:
            log.info("Opening config file...")
            with open("data/config.json", "r") as f:
                self.config = json.load(f)

        log.info("Loading programs from db...")
        self.load_programs()

        log.info("Deleting unfinished time entries...")
        TimeEntry.delete_unfinished_entries()
        log.info("Starting activity loop...")

        # create a queue for running functions in the main thread from
        # other threads
        self.request_queue = queue.Queue()
        self.result_queue = queue.Queue()

        # start the queue loop
        self.queue_loop()

        # create the activity loop thread and start it
        self.activity_thread = threading.Thread(target=self.activity_loop)
        self.activity_thread.daemon = True  # close the thread when the app is destroyed
        self.activity_thread.start()

        # create the multiprocess listener
        partial = functools.partial(self.submit_to_queue, self.start_gui)
        self.multiprocess_listener = threading.Thread(target=utils.multiprocess_listener, args=(partial,))
        self.multiprocess_listener.daemon = True  # close the thread when the app is destroyed
        self.multiprocess_listener.start()

        # create the updater loop
        self.updater_thread = threading.Thread(target=updater.updater_loop, args=(master,))
        self.updater_thread.daemon = True  # close the thread when the app is destroyed
        self.updater_thread.start()

        self.main_display = None

        if not no_gui:
            self.start_gui()

    def start_gui(self):
        """Registers and starts the GUI"""
        log.info("Registering MainDisplay...")

        self.master.deiconify()

        if self.main_display:
            log.info("MainDisplay is already registered, aborting...")
            # TODO: make already open window appear in front
            return

        self.main_display = MainDisplay(self)
        self.main_display.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

    def destroy_gui(self):
        log.info("Destroying MainDisplay...")

        if not self.main_display:
            raise RuntimeError("No GUI to destroy!")

        self.main_display.destroy()
        self.master.withdraw()
        self.main_display = None

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

    def submit_to_queue(self, callable, *args, **kwargs):
        """Submit a callable to fun from another thread"""
        self.request_queue.put((callable, args, kwargs))
        return self.result_queue.get()

    def queue_loop(self):
        """Loop that runs callables from other threads"""
        try:
            callable, args, kwargs = self.request_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            retval = callable(*args, **kwargs)
            self.result_queue.put(retval)

        self.after(500, self.queue_loop)

    def activity_loop(self):
        """Main activity loop that does all the program detection

        This loop checks if any of the programs are open, if they are active, and
        whether or not the mouse is active.

        Since it is in run in another thread, all database calls must be
        submitted to the queue to be run in the main thread.
        """
        while True:
            # check immediately if the user is inactive to save on processing time
            time_since = utils.get_idle_time()
            if time_since > int(self.config["mouse_timeout"]):
                if self.current_program:
                    log.info(
                        f"It's been {self.config['mouse_timeout']} second since last active, "
                        f"stopping logging program {self.current_program}"
                    )
                    self.submit_to_queue(
                        self.stop_logging_program, self.current_program
                    )
                    self.current_program = None

                # doing this here so we can return and not worry about indenting
                time.sleep(0.5)
                continue

            # we need to submit this to the queue to run it in the main thread
            # since it is a call to the db
            def get_program_names():
                return {p.process_name: p for p in self.programs}

            # if the current program isn't set, check if one of the programs
            # is an active window
            program_names = self.submit_to_queue(get_program_names)
            processes = utils.get_processes(program_names.keys())

            if processes:
                # loop through processes to see if there's an active one
                active_program = None
                for name, proc in processes.items():
                    if utils.is_active_window(proc.pid):
                        active_program = program_names[name]
                        break

                if self.current_program:
                    # if the current program is set but there is no longer
                    # an active program, stop logging the current program and
                    # set the current program to None
                    if not active_program:
                        log.info(
                            f"Current program {self.current_program} is no longer running, stopping logs"
                        )
                        self.submit_to_queue(
                            self.stop_logging_program, self.current_program
                        )
                        self.current_program = None

                    # if the current program is set and there's a new active program,
                    # stop logging the current program and start logging the new one
                    # while setting the current program to the new one
                    elif self.current_program != active_program:
                        log.info(
                            f"Current program {self.current_program} is no longer running, "
                            f"but new program {active_program} is. "
                            "stopping old and starting new logs"
                        )
                        self.submit_to_queue(
                            self.stop_logging_program, self.current_program
                        )
                        self.submit_to_queue(self.start_logging_program, active_program)
                        self.current_program = active_program

                else:
                    # if there's an active program but no current program set,
                    # just start logging the active program and set the current
                    # program to the active program
                    if active_program:
                        log.info(
                            f"Current program {active_program} has started, starting logs"
                        )
                        self.submit_to_queue(self.start_logging_program, active_program)
                        self.current_program = active_program

            time.sleep(0.5)
