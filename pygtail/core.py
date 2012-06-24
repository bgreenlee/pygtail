#!/usr/bin/python -tt
# -*- coding: utf-8 -*-

# pygtail - a python "port" of logtail2
# Copyright (C) 2011 Brad Greenlee <brad@footle.org>
#
# Derived from logcheck <http://logcheck.org>
# Copyright (C) 2003 Jonathan Middleton <jjm@ixtab.org.uk>
# Copyright (C) 2001 Paul Slootman <paul@debian.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from os import stat, linesep
from os.path import exists, getsize
import sys
import glob
import string
import time
from optparse import OptionParser

__version__ = '0.2.1'


class Pygtail(object):
    """
    Creates an iterable object that returns only unread lines.
    """
    def __init__(self, filename, offset_file=None, paranoid=False, follow=False):
        self.filename = filename
        self.paranoid = paranoid
        self._offset_file = offset_file or "%s.offset" % self.filename

        self._follow = follow

        self.restart()

    def restart(self):
        self._offset_file_inode = 0
        self._offset = 0
        self._fh = None
        self._rotated_logfile = None

        # if offset file exists and non-empty, open and parse it
        if exists(self._offset_file) and getsize(self._offset_file):
            offset_fh = open(self._offset_file, "r")
            (self._offset_file_inode, self._offset) = \
                [int(line.strip()) for line in offset_fh]
            offset_fh.close()
            if self._offset_file_inode != stat(self.filename).st_ino:
                # The inode has changed, so the file might have been rotated.
                # Look for the rotated file and process that if we find it.
                self._rotated_logfile = self._determine_rotated_logfile()

    def __del__(self):
        self._update_offset_file()
        if self._filehandle():
            self._filehandle().close()

    def __iter__(self):
        return self

    def next(self):
        """
        Return the next line in the file, updating the offset.
        """

        while True:
            result = self._next()

            if result is not None:
                return result

    def _current_file_next_line(self):
        fh = self._filehandle()
        old_position = fh.tell()

        try:
            line = next(fh)
        except StopIteration:
            # might look like a no-op as we're already there (given the file
            # iterator just told us we're at EOF), but seeking there again
            # restarts the iteration process. thus, when we next call this
            # function an the file grew in the meantime, things will be up and
            # running again.
            fh.seek(old_position)
            raise

        if not line.endswith(linesep):
            fh.seek(old_position)
            raise StopIteration("Not at EOF yet, but nothing complete to yield either.")

        return line

    def _next(self):
        try:
            return self._current_file_next_line()
        except StopIteration:
            # we've reached the end of the file; if we're processing the
            # rotated log file, we can continue with the actual file; otherwise
            # update the offset file
            if self._rotated_logfile:
                self._rotated_logfile = None
                self._fh.close()
                self._offset = 0
                # don't open up current logfile, just make the next() try again

                return None

            else: # we're in the real file, it's over for good (at least for now)
                if self._follow:
                    time.sleep(self._follow)
                    return None
                else:
                    self._update_offset_file()
                    raise
        finally:
            if self.paranoid:
                self._update_offset_file()

    def __next__(self):
        """`__next__` is the Python 3 version of `next`"""
        return self.next()

    def readlines(self):
        """
        Read in all unread lines and return them as a list.
        """
        return [line for line in self]

    def read(self):
        """
        Read in all unread lines and return them as a single string.
        """
        lines = self.readlines()
        if lines:
            return ''.join(lines)
        else:
            return None

    def _filehandle(self):
        """
        Return a filehandle to the file being tailed, with the position set
        to the current offset.
        """
        if not self._fh or self._fh.closed:
            filename = self._rotated_logfile or self.filename
            self._fh = open(filename, "r")
            self._fh.seek(self._offset)

        return self._fh

    def _update_offset_file(self):
        """
        Update the offset file with the current inode and offset.
        """
        offset = self._filehandle().tell()
        inode = stat(self.filename).st_ino
        fh = open(self._offset_file, "w")
        fh.write("%s\n%s\n" % (inode, offset))
        fh.close()

    def _determine_rotated_logfile(self):
        """
        We suspect the logfile has been rotated, so try to guess what the
        rotated filename is, and return it.
        """
        rotated_filename = self._check_rotated_filename_candidates()
        if (rotated_filename and exists(rotated_filename) and
            stat(rotated_filename).st_ino == self._offset_file_inode):
            return rotated_filename
        else:
            return None

    def _check_rotated_filename_candidates(self):
        """
        Check for various rotated logfile filename patterns and return the first
        match we find.
        """
        # savelog(8)
        candidate = "%s.0" % self.filename
        if (exists(candidate) and exists("%s.1.gz" % self.filename) and
            (stat(candidate).st_mtime > stat("%s.1.gz" % self.filename).st_mtime)):
            return candidate

        # logrotate(8)
        candidate = "%s.1" % self.filename
        if exists(candidate):
            return candidate

        # dateext rotation scheme
        candidates = glob.glob("%s-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]" % self.filename)
        if candidates:
            candidates.sort()
            return candidates[-1]  # return most recent

        # no match
        return None


def main():
    # command-line parsing
    cmdline = OptionParser(usage="usage: %prog [options] logfile",
        description="Print log file lines that have not been read.",
        version=__version__)
    cmdline.add_option("--offset-file", "-o", action="store",
        help="File to which offset data is written (default: <logfile>.offset).")
    cmdline.add_option("--paranoid", "-p", action="store_true",
        help="Update the offset file every time we read a line (as opposed to"
             " only when we reach the end of the file).")
    cmdline.add_option("--follow", "-f", action="store_true",
        help="Do not exit at the end of the file, but wait for new lines to be"
             " written.")

    options, args = cmdline.parse_args()

    if (len(args) != 1):
        cmdline.error("Please provide a logfile to read.")

    pygtail = Pygtail(args[0],
                      offset_file=options.offset_file,
                      paranoid=options.paranoid,
                      follow=options.follow)
    for line in pygtail:
        sys.stdout.write(line)


if __name__ == "__main__":
    main()
