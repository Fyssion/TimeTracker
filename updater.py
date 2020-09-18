"""Updates TimeTracker and its dependencies

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

import os
import json

import logging


log = logging.getLogger("timetracker.updater")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


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
