from collections import namedtuple

from . import models
from . import utils
from . import widgets
from . import updater

VersionInfo = namedtuple("VersionInfo", "major minor micro releaselevel serial")
version_info = VersionInfo(major=0, minor=1, micro=0, releaselevel="alpha", serial=0)

__version__ = "0.2.1"
__author__ = "Fyssion"
__copyright__ = "Copyright 2020 Fyssion"
__license__ = "MIT"
