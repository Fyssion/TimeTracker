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
import time
import threading
import Queue

import psutil
from pynput import mouse, keyboard

from models import session, Program, TimeEntry
import utils


log = logging.getLogger("timetracker")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


class ProgramTimeDisplay(tk.StringVar):
    """A counting stopwatch of time"""

    def __init__(self, timedelta, current_time):
        tk.StringVar.__init__(self)
        self.timedelta = timedelta
        self.current_time = current_time

    def update_time(self):
        """Update the time using """
        since = datetime.datetime.utcnow() - self.current_time
        final_timedelta = self.timedelta + since
        self.set(
            f"{final_timedelta.hours:02d}:{final_timedelta.minutes:02d}:{final_timedelta.seconds:02d}"
        )


class AddProgramDisplay(tk.Toplevel):
    def __init__(self, master=None):
        tk.Toplevel.__init__(self, master)

        self.title("Add a Program")

        name_text = tk.Message(self, text="Name your program")
        name_text.pack()

        name_entry = tk.Entry(self)
        name_entry.pack()

        self.program_dict = program_dict = utils.get_all_processes()
        dropdown_var = tk.StringVar()
        dropdown_var.set(program_dict.keys()[0])

        dropdown = tk.OptionMenu(self, dropdown_var, *program_dict.keys())
        dropdown.pack()

        save_button = tk.Button(self, text="Save", command=self.save_to_db)
        save_button.pack()

        cancel_button = tk.Button(self, text="Cancel", command=self.destroy)
        cancel_button.pack()

    def save_to_db(self):
        """Saves the current program to the database and destroys the display"""
        name = self.name_entry.get()
        if not name:
            # TODO: do something here that warns them I guess
            return

        option = self.dropdown.get()
        program = self.program_dict[option]

        # TODO: save the program to the db

        self.destroy()


class MainDisplay(tk.Frame):
    """Main display that greets the user upon opening

    This shows stats for today as well as the current activity time
    """

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        entries = []
        self.last_checked = None
        self.get_todays_time_entries()

        self.status = tk.StringVar()
        self.status.set(
            f"Counting {master.current_program}"
            if master.current_program
            else "Currently Paused"
        )

        # Create status label
        self.status_label = tk.Label(self)
        self.status_label.grid(column=0, row=0, sticky=tk.W)
        self.status_label["textvariable"] = self.status

        self.main_time = ProgramTimeDisplay(*self.calculate_timedelta(entries))

        # Create main counter label
        self.main_counter_label = tk.Label(self)
        self.main_counter_label.grid(column=0, row=1, sticky=tk.W)
        self.main_counter_label["textvariable"] = self.main_time

        # Add Program button
        self.add_program_button = tk.Button(
            self, text="Add Program", command=self.add_program
        )
        self.add_program_button.grid(column=1, row=0, sticky=tk.W)

        # Quit button
        self.quit_button = tk.Button(self, text="Quit", command=master.master.destroy)
        self.quit_button.grid(column=1, row=1, sticky=tk.W)

        for child in self.winfo_children():
            child.grid_configure(padx=20, pady=20)

    def add_program(self):
        """Opens a new window where you can add a program to track"""
        popup = AddProgramDisplay(self)

    def calculate_timedelta(self, all_entries, program_id=None):
        """Calculates a timedelta for a given program or all programs if None is passed"""
        if not program_id:
            entries = [e for e in all_entries]

        else:
            entries = [e for e in all_entries if e.program_id == program_id]

        total_timedelta = datetime.timedelta()
        current_time = None

        for i, entry in enumerate(reversed(entries)):
            if entry.end_datetime:
                total_timedelta += entry.end_datetime - entry.start_datetime

            elif i == len(entries) - 1:
                current_time = entry.start_datetime

        return total_timedelta, current_time

    def get_todays_time_entries(self):
        """Gets a list of today's entries so far"""
        today = datetime.datetime.today()
        todays_datetime = datetime.datetime(today.year, today.month, today.day)
        offset = datetime.datetime.now() - datetime.datetime.utcnow()
        utc_today = todays_datetime + offset

        # def is_today(entry_time):
        #     UTC_timestamp = float(entry_time.strftime("%s"))
        #     local_entry_time = datetime.datetime.fromtimestamp(UTC_timestamp)

        #     return local_entry_time >= todays_datetime

        entries = (
            session.query(TimeEntry)
            .filter(TimeEntry.start_datetime >= utc_today)
            .order_by(TimeEntry.end_datetime.desc())
        ).all()

        self.entries = entries
        self.last_checked = datetime.datetime.utcnow()


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

        # record mouse movement
        self.active_last = datetime.datetime.utcnow()
        # master.bind("<Motion>", self.on_activity)
        # master.bind("<KeyPress>", self.on_activity)
        mouse_listener = mouse.Listener(
            on_move=self.on_activity,
            on_click=self.on_activity,
            on_scroll=self.on_activity,
        )
        mouse_listener.start()

        kb_listener = keyboard.Listener(
            on_press=self.on_activity, on_release=self.on_activity
        )
        kb_listener.start()

        log.info("Loading programs from db")
        self.load_programs()

        log.info("Deleting unfinished time entries")
        TimeEntry.delete_unfinished_entries()
        log.info("Starting activity loop")

        self.request_queue = Queue.Queue()
        self.result_queue = Queue.Queue()

        self.queue_loop()

        self.activity_thread = threading.Thread(target=self.activity_loop)
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

    def submit_to_tkinter(self, callable, *args, **kwargs):
        """Submit a callable to fun from another thread"""
        self.request_queue.put((callable, args, kwargs))
        return self.result_queue.get()

    def queue_loop(self):
        """Loop that runs callables from other threads"""
        try:
            callable, args, kwargs = self.request_queue.get_nowait()
        except Queue.Empty:
            pass
        else:
            retval = callable(*args, **kwargs)
            self.result_queue.put(retval)

        self.after(500, self.queue_loop)

    def activity_loop(self):
        """Main activity loop that does all the program detection

        This loop checks if any of the programs are open, if they are active, and
        whether or not the mouse is active.
        """
        while True:

            # check immediately if the user is inactive to save on processing time
            time_since = datetime.datetime.utcnow() - self.active_last
            if time_since.seconds > int(
                self.config["mouse_timeout"]
            ):
                if self.current_program:
                    log.info(
                        f"It's been {self.config['mouse_timeout']} second since last active, "
                        f"stopping logging program {self.current_program}"
                    )
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
                        self.stop_logging_program(self.current_program)
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
                        self.stop_logging_program(self.current_program)
                        self.start_logging_program(active_program)
                        self.current_program = active_program

                else:
                    # if there's an active program but no current program set,
                    # just start logging the active program and set the current
                    # program to the active program
                    if active_program:
                        log.info(f"Current program {active_program} has started, starting logs")
                        self.start_logging_program(active_program)
                        self.current_program = active_program

            time.sleep(0.5)

        # self.after(500, self.activity_loop)

    def on_activity(self, *args):
        """Records the last time the user was active (for inactivity tracking)"""
        self.active_last = datetime.datetime.utcnow()


def check_pid():
    """Checks if another instance of the app is running"""
    filename = "instance_lock.txt"

    def write_pid():
        with open(filename, "w") as f:
            f.write(str(os.getpid()))

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
