from collections import namedtuple

VersionInfo = namedtuple("VersionInfo", "major minor micro releaselevel serial")
version_info = VersionInfo(major=0, minor=3, micro=0, releaselevel="final", serial=0)

__version__ = "0.3.0"
__author__ = "Fyssion"
__copyright__ = "Copyright 2020 Fyssion"
__license__ = "MIT"
