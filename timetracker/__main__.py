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
from tkinter import ttk
import tkinter.font as tk_font
import os
import json
import datetime
import argparse
import logging
import time
import threading
import queue
import sys

import psutil
import pynput

from models import session, Program, TimeEntry
import utils


log = logging.getLogger("timetracker")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


class AddProgramDisplay(tk.Toplevel):
    """A popup that lets you add a new program to track"""
    def __init__(self, master=None):
        tk.Toplevel.__init__(self, master)

        self.title("Add a Program")

        # name your program text
        name_text = tk.Message(self, text="Name your program")
        name_text.pack()

        # entry box for the program name
        # TODO: possibly make this autofill when a program is selected from
        # the dropdown
        self.name_entry = tk.Entry(self)
        self.name_entry.pack()

        # get a list of all processes running
        # FIXME: THIS TAKES FOREVER!!! ALSO IT SHOWS EVERY SINGLE PROCESS!!
        # TODO: make this only show open windows (without taking a century)
        self.program_dict = program_dict = utils.get_all_processes()
        sorted_keys = list(sorted(program_dict.keys(), key=lambda x: x.lower()))

        # make the dropdown
        dropdown_var = tk.StringVar()
        dropdown_var.set(sorted_keys[0])

        self.dropdown = ttk.Combobox(self, textvariable=dropdown_var, values=sorted_keys)
        self.dropdown.pack()

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

        to_add = Program(name=name, process_name=program.name(), location=program.exe())
        session.add(to_add)
        session.commit

        self.destroy()


class ProgramTimeDisplay(tk.StringVar):
    """A StringVar that displays the current timer time"""

    def __init__(self, timedelta, current_time):
        tk.StringVar.__init__(self)
        self.timedelta = timedelta
        self.current_time = current_time

    def update_attrs(self, timedelta, current_time):
        """Easy way to update attrs from MainDisplay.calculate_timedelta"""
        self.timedelta = timedelta
        self.current_time = current_time

    def update_time(self):
        """Update itself to the most recent time"""
        if not self.current_time:
            final_timedelta = self.timedelta

        else:
            since = datetime.datetime.utcnow() - self.current_time
            final_timedelta = self.timedelta + since

        hours = final_timedelta.seconds // 3600
        minutes = (final_timedelta.seconds // 60) % 60
        seconds = final_timedelta.seconds - (minutes * 60) - (hours * 3600)

        self.set(
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )


class MainDisplay(tk.Frame):
    """Main display that greets the user upon opening

    This shows stats for today as well as the current activity time
    """

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        self.last_checked = None
        entries = self.get_todays_time_entries()
        self.is_paused = True
        self.counting_program_id = None

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
        self.main_time.update_time()

        # Create main counter label
        counter_font = tk_font.Font(size=20)
        self.main_counter_label = tk.Label(self)
        self.main_counter_label.grid(column=0, row=1, sticky=tk.W)
        self.main_counter_label.configure(font=counter_font)
        self.main_counter_label["textvariable"] = self.main_time

        # Add Program button
        self.add_program_button = tk.Button(
            self, text="Add Program", command=self.add_program
        )
        self.add_program_button.grid(column=0, row=2, sticky=tk.W)

        # Quit button
        self.quit_button = tk.Button(self, text="Quit", command=master.master.destroy)
        self.quit_button.grid(column=1, row=2, sticky=tk.W)

        for child in self.winfo_children():
            child.grid_configure(padx=20, pady=20)

        self.counter_loop()

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

            elif i == 0:
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

        self.last_checked = datetime.datetime.utcnow()

        return entries

    def counter_loop(self):
        """Loop that counts up the counter"""

        # if the counter is paused and the current program doesn't exist,
        # then just keep being paused because nothing has changed
        if self.is_paused and self.master.current_program:
            entries = self.get_todays_time_entries()
            self.main_time.update_attrs(*self.calculate_timedelta(entries))
            self.main_time.update_time()
            self.counting_program_id = self.master.current_program.id
            self.is_paused = False
            self.status.set(f"Tracking {self.master.current_program.name}")

        # if the counter isn't paused and the current program doesn't exist,
        # then the logging and stopped and the counter should too
        elif not self.is_paused and not self.master.current_program:
            entries = self.get_todays_time_entries()
            self.main_time.update_attrs(*self.calculate_timedelta(entries))
            self.main_time.update_time()
            self.is_paused = True
            self.counting_program_id = None
            self.status.set(f"Currently Paused")

        # if the counter isn't paused and the current program matches the program we're currently
        # counting, then just update the time again because nothing has changed
        elif not self.is_paused and self.master.current_program.id == self.counting_program_id:
            self.main_time.update_time()

        # finally, if the counter isn't paused and the current program doesn't match
        # the program we're currently counting, then the program has changed since
        # the last loop and we need to check the db again
        elif not self.is_paused and self.master.current_program.id != self.counting_program_id:
            entries = self.get_todays_time_entries()
            self.main_time.update_attrs(*self.calculate_timedelta(entries))
            self.main_time.update_time()
            self.counting_program_id = self.master.current_program.id

        self.after(1000, self.counter_loop)


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

        # self.after(500, self.activity_loop)


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
    sys.exit()


if __name__ == "__main__":
    main()
