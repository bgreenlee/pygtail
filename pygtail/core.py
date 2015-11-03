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
from stat import S_IFREG
from os import stat, listdir, walk
from os.path import exists, getsize, basename
from os.path import join as path_join
import sys
import glob
import gzip
from optparse import OptionParser


__version__ = '0.6.1'


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
    """
    def __init__(self, filename, offset_file=None, paranoid=False, copytruncate=True,
                 every_n=0, on_update=False, use_update_file=True):
        self.filename = filename
        self.paranoid = paranoid
        self.every_n = every_n
        self.on_update = on_update
        self.copytruncate = copytruncate
        self._offset_file = offset_file or "%s.offset" % self.filename
        self._offset_file_inode = 0
        self._offset = 0
        self._since_update = 0
        self._fh = None
        self._rotated_logfile = None
        self._use_update_file = use_update_file

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
            # rotated log file, we can continue with the actual file; otherwise
            # update the offset file
            if self._rotated_logfile:
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
                self._fh = open(filename, "r")
            self._fh.seek(self._offset)

        return self._fh

    def _update_offset_file(self):
        """
        Update the offset file with the current inode and offset.
        """
        if self.on_update:
            self.on_update()
        
        if self._use_update_file:
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

        # dateext rotation scheme
        candidates = glob.glob("%s-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]" % self.filename)
        if candidates:
            candidates.sort()
            return candidates[-1]  # return most recent

        # for TimedRotatingFileHandler
        candidates = glob.glob("%s.[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]" % self.filename)
        if candidates:
            candidates.sort()
            return candidates[-1]  # return most recent

        # no match
        return None

    def _get_next_line(self):
        # flush handle before reading; this helps emulate `tail -f` behavior.
        self._filehandle().flush()
        line = self._filehandle().readline()
        if not line:
            raise StopIteration
        self._since_update += 1
        return line

class Pygdir(object):
    """
    Create a monitor object for a specified directory. 

    Every time the iterator object is queried, the file set is also updated.

    base_dir        The directory to monitor

    Other parameters are passed as-is into Pygtail.
    """
    def __init__(self, base_dir, filter_func=None, base_dir_glob=None, paranoid=False, copytruncate=True,
                 every_n=0, on_update=False):
        self._base_dir = base_dir
        self._base_dir_glob = base_dir_glob
        self._file_set = {}
        self._paranoid = paranoid
        self._copytruncate = copytruncate
        self._every_n = every_n
        self._on_update = on_update
        self._filter_func = filter_func

    def _make_filename(self, filename):
        return path_join(self._base_dir, filename)

    def _get_all_base_dir_files(self):
        if self._base_dir_glob is not None:
            return [y for x in walk(self._base_dir) for y in glob.glob(path_join(x[0], self._base_dir_glob))]
        else:
            return listdir(self._base_dir)

    def _regular_files_in_dir(self):
        return filter(self._filter_func, [f for f in self._get_all_base_dir_files() if stat(self._make_filename(f)).st_mode & S_IFREG > 0])

    def _update_file_set(self):
        """
        Update the file set to be monitored: all new files are added, existing files aren't touched.

        XXX: This could mean that if an I/O error occurs (e.g., a monitored file is deleted, and then re-created) we would stop monitoring that file.
        """
        def make_pygtail(filename):
            return Pygtail(self._make_filename(filename), None, self._paranoid, self._copytruncate, self._every_n, self._on_update, False)
        self._file_set.update({f:make_pygtail(f) 
            for f in self._regular_files_in_dir() 
                if f not in self._file_set.keys()})
    
    def __next__(self):
        return self.next()

    def next(self):

        # XXX: consider moving this to after iteration; starvation could occur either way.
        # Either super-active old files will choke out new files, or many-created files will choke out old files. Currently, the code errs on side of few creations and many additions
        self._update_file_set()
        for p in self._file_set.values():
            try:
                return p.__next__()
            except StopIteration:
                # eat the exception and continue trying to find
                # an entry with a next line
                pass

        # we're out of files, so really no more lines
        raise StopIteration

    def __iter__(self):
        return self

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
                      copytruncate=not options.no_copytruncate)

    for line in pygtail:
        sys.stdout.write(line)


if __name__ == "__main__":
    main()
