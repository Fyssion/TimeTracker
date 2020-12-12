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
import datetime

from .models import session, Program, TimeEntry
from . import utils


class YesNoPrompt(tk.Toplevel):
    def __init__(self, master=None, question=None):
        tk.Toplevel.__init__(self, master)

        self.result = None

        self.title("Update TimeTracker")

        header = tk.Label(self, text=question)
        header.grid(column=0, row=0, sticky=tk.W, padx=20, pady=5)

        yes_button = tk.Button(self, text="Yes", command=self.yes)
        yes_button.grid(column=0, row=1, sticky=tk.W, padx=(20, 5), pady=5)

        no_button = tk.Button(self, text="No", command=self.no)
        no_button.grid(column=0, row=1, sticky=tk.E, padx=(5, 20), pady=5)

    def yes(self):
        self.result = True
        self.destroy()

    def no(self):
        self.result = False
        self.destroy()


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

        try:
            program = self.program_dict[option]
        except KeyError:
            # TODO: warning thingy like above
            return

        to_add = Program(name=name, process_name=program.name(), location=program.exe())
        session.add(to_add)
        session.commit()

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
        # if we're paused, we don't need to add anything to the timedelta
        if not self.current_time:
            final_timedelta = self.timedelta

        # if we aren't paused, we need to add the time since start to the timedelta
        else:
            since = datetime.datetime.utcnow() - self.current_time
            final_timedelta = self.timedelta + since

        hours = final_timedelta.seconds // 3600
        minutes = (final_timedelta.seconds // 60) % 60
        seconds = final_timedelta.seconds - (minutes * 60) - (hours * 3600)

        self.set(
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )


class ProgramTime:
    def __init__(self, program, timedelta, current_time):
        self.program = program
        self.timedelta = timedelta
        self.current_time = current_time
        self.final_timedelta = None


class ProgramListDisplay(tk.StringVar):
    """A StingVar that displays the user's list of programs"""
    def __init__(self, program_times):
        tk.StringVar.__init__(self)
        self.set("Loading programs...")
        self.program_times = program_times

    def update_attrs(self, program_times):
        """Easy way to update attrs"""
        self.program_times = program_times

    def resolve_timedelta(self, timedelta, current_time):
        """Calculate the timedelta based on the current time"""
        if not current_time:
            final_timedelta = timedelta

        else:
            since = datetime.datetime.utcnow() - current_time
            final_timedelta = timedelta + since

        return final_timedelta

    def generate_program_time(self, timedelta):
        """Generate a time string"""
        hours = timedelta.seconds // 3600
        minutes = (timedelta.seconds // 60) % 60
        seconds = timedelta.seconds - (minutes * 60) - (hours * 3600)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def update_programs(self):
        """Update the StringVar with a new set of programs"""
        results = []

        def edit_timedelta(p):
            final_timedelta = self.resolve_timedelta(p.timedelta, p.current_time)
            p.final_timedelta = final_timedelta
            return p

        program_times = [edit_timedelta(p) for p in self.program_times]
        program_times.sort(key=lambda p: p.timedelta, reverse=True)

        for i, program_time in enumerate(program_times):
            program = program_time.program
            timedelta = program_time.final_timedelta
            delta = self.generate_program_time(timedelta)
            results.append(f"{i+1}. {program.name} - {delta}")

        if not results:
            self.set("No programs added. Add some to begin tracking!")

        else:
            self.set("\n".join(results))


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

        header_font = tk_font.Font(size=16)

        # == Main counter section ==

        # Create status label
        self.status_label = tk.Label(self, font=header_font)
        self.status_label.grid(column=0, row=0, sticky=tk.W, padx=20, pady=5)
        self.status_label["textvariable"] = self.status

        self.main_time = ProgramTimeDisplay(*self.calculate_timedelta(entries))
        self.main_time.update_time()

        # Create main counter label
        self.main_counter_label = tk.Label(self, font=tk_font.Font(size=40))
        self.main_counter_label.grid(column=0, row=1, sticky=tk.W, padx=20, pady=5)
        self.main_counter_label["textvariable"] = self.main_time

        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        separator.grid(column=0, row=2, sticky=(tk.W, tk.E), padx=20)

        # == Programs section ==
        self.program_header = tk.Label(self, text="Programs", font=header_font)
        self.program_header.grid(column=0, row=3, sticky=tk.W, padx=20, pady=(10, 2))

        # Actual list of programs
        self.programs_var = ProgramListDisplay(self.get_program_times(entries))
        self.programs_var.update_programs()

        self.program_list_label = tk.Label(self, font=tk_font.Font(size=11), justify=tk.LEFT)
        self.program_list_label.grid(column=0, row=4, sticky=tk.W, padx=20, pady=2)
        self.program_list_label["textvariable"] = self.programs_var

        # Add Program button
        self.add_program_button = tk.Button(
            self, text="Add Program", command=self.add_program
        )
        self.add_program_button.grid(column=0, row=5, sticky=tk.W, padx=20, pady=10)

        # Quit button
        self.quit_button = tk.Button(self, text="Quit", command=master.destroy_gui)
        self.quit_button.grid(column=1, row=5, sticky=tk.W, padx=20, pady=20)

        # for child in self.winfo_children():
        #     child.grid_configure(padx=20, pady=20)

        self.counter_loop()

    def add_program(self):
        """Opens a new window where you can add a program to track"""
        popup = AddProgramDisplay(self)
        self.wait_window(popup)
        self.master.load_programs()
        self.programs_var.update_programs(self.master.programs)

    def get_program_times(self, all_entries):
        """Generates a list of :class:`ProgramTime`s to be used in the :class:`ProgramListDisplay"""
        program_times = []

        for program in self.master.programs:
            timedelta, current_time = self.calculate_timedelta(all_entries, program_id=program.id)
            program_times.append(ProgramTime(program, timedelta, current_time))

        return program_times

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
        utc_today = todays_datetime - offset

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
            self.programs_var.update_attrs(self.get_program_times(entries))
            self.programs_var.update_programs()
            self.counting_program_id = self.master.current_program.id
            self.is_paused = False
            self.status.set(f"Tracking {self.master.current_program.name}")

        # if the counter isn't paused and the current program doesn't exist,
        # then the logging stopped and the counter should too
        elif not self.is_paused and not self.master.current_program:
            entries = self.get_todays_time_entries()
            self.main_time.update_attrs(*self.calculate_timedelta(entries))
            self.main_time.update_time()
            self.programs_var.update_attrs(self.get_program_times(entries))
            self.programs_var.update_programs()
            self.is_paused = True
            self.counting_program_id = None
            self.status.set("Currently Paused")

        # if the counter isn't paused and the current program matches the program we're currently
        # counting, then just update the time again because nothing has changed
        elif not self.is_paused and self.master.current_program.id == self.counting_program_id:
            self.main_time.update_time()
            self.programs_var.update_programs()

        # finally, if the counter isn't paused and the current program doesn't match
        # the program we're currently counting, then the program has changed since
        # the last loop and we need to check the db again
        elif not self.is_paused and self.master.current_program.id != self.counting_program_id:
            entries = self.get_todays_time_entries()
            self.main_time.update_attrs(*self.calculate_timedelta(entries))
            self.main_time.update_time()
            self.programs_var.update_attrs(self.get_program_times(entries))
            self.programs_var.update_programs()
            self.counting_program_id = self.master.current_program.id

        self.after(1000, self.counter_loop)
