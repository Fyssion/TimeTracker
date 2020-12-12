from collections import namedtuple

VersionInfo = namedtuple("VersionInfo", "major minor micro releaselevel serial")
version_info = VersionInfo(major=0, minor=1, micro=0, releaselevel="alpha", serial=0)

__version__ = "0.2.2"
__author__ = "Fyssion"
__copyright__ = "Copyright 2020 Fyssion"
__license__ = "MIT"
