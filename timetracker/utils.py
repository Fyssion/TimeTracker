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


import win32process
import win32gui
import psutil
import win32api
import time
import os.path
import multiprocessing.connection
import logging
import tempfile

LOCKFILE = os.path.normpath(tempfile.gettempdir() + '/timetracker_instance.lock')


def write_pid():
    """Writes the app's PID to the lockfile"""
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))


def is_already_running():
    """Checks if another instance of the app is running"""
    if not os.path.isfile(LOCKFILE):
        write_pid()
        return False

    with open(LOCKFILE, "r") as f:
        other_pid = int(f.read())

    try:
        proc = psutil.Process(other_pid)
        return proc  # process exists and is running

    except psutil.NoSuchProcess:
        # process existed but is no longer running
        # replace old pid with our new one
        write_pid()
        return False


def delete_lockfile():
    """Deletes the lockfile if it exists"""
    if os.path.isfile(LOCKFILE):
        os.remove(LOCKFILE)
        return True


def top_level_windows(pid):
    """Returns a list of all top-level windows for a given pid"""

    def enumHandler(hwnd, data):
        if win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
            windows.append(hwnd)
        return True

    windows = []
    win32gui.EnumWindows(enumHandler, 0)
    return windows


def window_minimized(pid):
    """Returns whether or not a window is minimized"""
    for hwnd in top_level_windows(pid):
        if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
            return False
    return True


def is_active_window(pid):
    """Detects whether a window is the active window"""
    hwnd = win32gui.GetForegroundWindow()
    return pid == win32process.GetWindowThreadProcessId(hwnd)[1]


def program_active(pid):
    """Returns whether or not a program is active"""
    return not window_minimized(pid)  # haha yes it's dumb


def get_process(process_name):
    """
    Checks if there is any running process that contains the given process name
    """
    for process in psutil.process_iter():
        try:
            if process_name.lower() in process.name().lower():
                return process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None


def get_processes(process_names):
    """Checks if there are any running processes that contain the given process names

    Basically get_process but checks gets multiple processes
    """
    # process_name: psutil.Process
    processes = {}
    for proc in psutil.process_iter():
        try:
            proc_name = proc.name().lower()
            processes.update({n: proc for n in process_names if n.lower() in proc_name})

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return processes


def get_all_processes():
    """Returns a dict of the process name to the psutil.Process"""
    processes = {}
    for proc in psutil.process_iter():
        try:
            proc_name = proc.name()
            processes[proc_name] = proc

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return processes


def get_idle_time():
    """Gets the time in seconds since last idle"""
    return (win32api.GetTickCount() - win32api.GetLastInputInfo()) / 1000.0


def multiprocess_listener(callback, message="open_gui"):
    """Listen for messages from other processes

    This is used for opening the GUI.
    """
    log = logging.getLogger("timetracker.listener")

    address = ("localhost", 8320)  # family is deduced to be 'AF_INET'
    listener = multiprocessing.connection.Listener(address, authkey=b"hello_world")

    while True:
        conn = listener.accept()
        log.info(f"Connection accepted from {listener.last_accepted}")

        while True:
            msg = conn.recv()

            if msg == message:
                log.info(
                    f"Connection {listener.last_accepted} requested the GUI to be opened"
                )
                callback()

            elif msg == "close":
                log.info(f"Connection {listener.last_accepted} is closing the connection")
                conn.close()
                break

    listener.close()


def multiprocess_sender(msg="open_gui"):
    """Send a message to another process.

    See :func:`multiprocess_listener`
    """
    address = ("localhost", 8320)
    conn = multiprocessing.connection.Client(address, authkey=b"hello_world")
    conn.send(msg)
    conn.send("close")
    conn.close()


def loop(seconds, callback):
    """Call a function every x seconds"""
    while True:
        callback()
        time.sleep(seconds)
