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


def mouse_movement_listener(callback):
    """Listens for mouse movement and calls the callback when it catches some.

    This is meant to be run in a thread.
    """
    savedpos = win32api.GetCursorPos()

    while True:
        curpos = win32api.GetCursorPos()
        if savedpos != curpos:
            savedpos = curpos
            callback()
        time.sleep(0.05)


def mouse_click_listener(callback):
    """Listens for mouse clicks and calls the callback when it catches one.

    This is meant to be run in a thread.
    """
    # left button down = 0 or 1. button up = -127 or -128
    left_state = win32api.GetKeyState(0x01)
    # right button down = 0 or 1. button up = -127 or -128
    right_state = win32api.GetKeyState(0x02)

    while True:
        left_current = win32api.GetKeyState(0x01)
        right_current = win32api.GetKeyState(0x02)

        if left_current != left_state:  # button state changed
            left_state = left_current
            callback()

        if right_current != right_state:  # button state changed
            right_state = right_current
            callback()

        time.sleep(0.001)
