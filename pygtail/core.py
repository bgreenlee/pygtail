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

from __future__ import print_function
from os import fstat, stat
import os
from os.path import exists, getsize
import sys
import glob
import gzip
from optparse import OptionParser

__version__ = '0.10.0'


PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
else:
    text_type = unicode


def force_text(s, encoding='utf-8', errors='strict'):
    if isinstance(s, text_type):
        return s
    return s.decode(encoding, errors)


class Pygtail(object):
    """
    Creates an iterable object that returns only unread lines.

    Keyword arguments:
    offset_file   File to which offset data is written (default: <logfile>.offset).
    paranoid      Update the offset file every time we read a line (as opposed to
                  only when we reach the end of the file (default: False))
    every_n       Update the offset file every n'th line (as opposed to only when
                  we reach the end of the file (default: 0))
    on_update     Execute this function when offset data is written (default False)
    copytruncate  Support copytruncate-style log rotation (default: True)
    log_patterns  List of custom rotated log patterns to match (default: None)
    """
    def __init__(self, filename, offset_file=None, paranoid=False, copytruncate=True,
                 every_n=0, on_update=False, read_from_end=False, log_patterns=None):
        self.filename = filename
        self.paranoid = paranoid
        self.every_n = every_n
        self.on_update = on_update
        self.copytruncate = copytruncate
        self.read_from_end = read_from_end
        self.log_patterns = log_patterns
        self._offset_file = offset_file or "%s.offset" % self.filename
        self._offset_file_inode = 0
        self._offset = 0
        self._since_update = 0
        self._fh = None
        self._rotated_logfile = None

        # if offset file exists and non-empty, open and parse it
        if exists(self._offset_file) and getsize(self._offset_file):
            offset_fh = open(self._offset_file, "r")
            (self._offset_file_inode, self._offset) = \
                [int(line.strip()) for line in offset_fh]
            offset_fh.close()
            if self._offset_file_inode != stat(self.filename).st_ino or \
                    stat(self.filename).st_size < self._offset:
                # The inode has changed or filesize has reduced so the file
                # might have been rotated.
                # Look for the rotated file and process that if we find it.
                self._rotated_logfile = self._determine_rotated_logfile()

    def __del__(self):
        if self._filehandle():
            self._filehandle().close()

    def __iter__(self):
        return self

    def next(self):
        """
        Return the next line in the file, updating the offset.
        """
        try:
            line = self._get_next_line()
        except StopIteration:
            # we've reached the end of the file; if we're processing the
            # rotated log file or the file has been renamed, we can continue with the actual file; otherwise
            # update the offset file
            if self._is_new_file():
                self._rotated_logfile = None
                self._fh.close()
                self._offset = 0
                # open up current logfile and continue
                try:
                    line = self._get_next_line()
                except StopIteration:  # oops, empty file
                    self._update_offset_file()
                    raise
            else:
                self._update_offset_file()
                raise

        if self.paranoid:
            self._update_offset_file()
        elif self.every_n and self.every_n <= self._since_update:
            self._update_offset_file()

        return line

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
            try:
                return ''.join(lines)
            except TypeError:
                return ''.join(force_text(line) for line in lines)
        else:
            return None

    def _is_closed(self):
        if not self._fh:
            return True
        try:
            return self._fh.closed
        except AttributeError:
            if isinstance(self._fh, gzip.GzipFile):
                # python 2.6
                return self._fh.fileobj is None
            else:
                raise

    def _filehandle(self):
        """
        Return a filehandle to the file being tailed, with the position set
        to the current offset.
        """
        if not self._fh or self._is_closed():
            filename = self._rotated_logfile or self.filename
            if filename.endswith('.gz'):
                self._fh = gzip.open(filename, 'r')
            else:
                self._fh = open(filename, "r", 1)
            if self.read_from_end and not exists(self._offset_file):
                self._fh.seek(0, os.SEEK_END)
            else:
                self._fh.seek(self._offset)

        return self._fh

    def _update_offset_file(self):
        """
        Update the offset file with the current inode and offset.
        """
        if self.on_update:
            self.on_update()
        offset = self._filehandle().tell()
        inode = stat(self.filename).st_ino
        fh = open(self._offset_file, "w")
        fh.write("%s\n%s\n" % (inode, offset))
        fh.close()
        self._since_update = 0

    def _determine_rotated_logfile(self):
        """
        We suspect the logfile has been rotated, so try to guess what the
        rotated filename is, and return it.
        """
        rotated_filename = self._check_rotated_filename_candidates()
        if rotated_filename and exists(rotated_filename):
            if stat(rotated_filename).st_ino == self._offset_file_inode:
                return rotated_filename

            # if the inode hasn't changed, then the file shrank; this is expected with copytruncate,
            # otherwise print a warning
            if stat(self.filename).st_ino == self._offset_file_inode:
                if self.copytruncate:
                    return rotated_filename
                else:
                    sys.stderr.write(
                        "[pygtail] [WARN] file size of %s shrank, and copytruncate support is "
                        "disabled (expected at least %d bytes, was %d bytes).\n" %
                        (self.filename, self._offset, stat(self.filename).st_size))

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
        # with delaycompress
        candidate = "%s.1" % self.filename
        if exists(candidate):
            return candidate

        # without delaycompress
        candidate = "%s.1.gz" % self.filename
        if exists(candidate):
            return candidate

        rotated_filename_patterns = [
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d` + with `delaycompress`
            "%s-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]",
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d` + without `delaycompress`
            "%s-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].gz",
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d-%s` + with `delaycompress`
            "%s-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]",
            # logrotate dateext rotation scheme - `dateformat -%Y%m%d-%s` + without `delaycompress`
            "%s-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].gz",
            # for TimedRotatingFileHandler
            "%s.[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",
        ]
        if self.log_patterns:
            rotated_filename_patterns.extend(self.log_patterns)

        # break into directory and filename components to support cases where the
        # the file is prepended as part of rotation
        file_dir, rel_filename = os.path.split(self.filename)
        for rotated_filename_pattern in rotated_filename_patterns:
            candidates = glob.glob(os.path.join(file_dir, rotated_filename_pattern % rel_filename))
            if candidates:
                candidates.sort()
                return candidates[-1]  # return most recent

        # no match
        return None

    def _is_new_file(self):
        # Processing rotated logfile or at the end of current file which has been renamed
        return self._rotated_logfile or \
               self._filehandle().tell() == fstat(self._filehandle().fileno()).st_size and \
               fstat(self._filehandle().fileno()).st_ino != stat(self.filename).st_ino

    def _get_next_line(self):
        line = self._filehandle().readline()
        if not line:
            raise StopIteration
        self._since_update += 1
        return line


def main():
    # command-line parsing
    cmdline = OptionParser(usage="usage: %prog [options] logfile",
        description="Print log file lines that have not been read.")
    cmdline.add_option("--offset-file", "-o", action="store",
        help="File to which offset data is written (default: <logfile>.offset).")
    cmdline.add_option("--paranoid", "-p", action="store_true",
        help="Update the offset file every time we read a line (as opposed to"
             " only when we reach the end of the file).")
    cmdline.add_option("--every-n", "-n", action="store",
        help="Update the offset file every n'th time we read a line (as opposed to"
             " only when we reach the end of the file).")
    cmdline.add_option("--no-copytruncate", action="store_true",
        help="Don't support copytruncate-style log rotation. Instead, if the log file"
             " shrinks, print a warning.")
    cmdline.add_option("--read-from-end", action="store_true",
        help="Read log file from the end if offset file is missing. Useful for large files.")
    cmdline.add_option("--log-pattern", action="append",
        help="Custom log rotation glob pattern. Use %s to represent the original filename."
             " You may use this multiple times to provide multiple patterns.")
    cmdline.add_option("--version", action="store_true",
        help="Print version and exit.")

    options, args = cmdline.parse_args()

    if options.version:
        print("pygtail version", __version__)
        sys.exit(0)

    if (len(args) != 1):
        cmdline.error("Please provide a logfile to read.")

    if options.every_n:
        options.every_n = int(options.every_n)
    pygtail = Pygtail(args[0],
                      offset_file=options.offset_file,
                      paranoid=options.paranoid,
                      every_n=options.every_n,
                      copytruncate=not options.no_copytruncate,
                      read_from_end=options.read_from_end,
                      rotated_filename_patterns=options.log_pattern)

    for line in pygtail:
        sys.stdout.write(line)


if __name__ == "__main__":
    main()
