import tkinter as tk
import os
import json
import time
import threading
import queue
import logging

from widgets import MainDisplay
from models import session, Program, TimeEntry
import utils

log = logging.getLogger(__name__)


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
                json.dump(default_config, f, indent=4, sort_keys=True)
                self.config = default_config

        else:
            log.info("Opening config file")
            with open("data/config.json", "r") as f:
                self.config = json.load(f)

        log.info("Loading programs from db")
        self.load_programs()

        log.info("Deleting unfinished time entries")
        TimeEntry.delete_unfinished_entries()
        log.info("Starting activity loop")

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
