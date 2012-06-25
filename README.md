pygtail
=======

A python "port" of [logcheck's logtail2](http://logcheck.org).

Pygtail reads log file lines that have not been read. It will even handle log
files that have been rotated.

Usage
-----

From the command line:

    Usage: pygtail.py [options] logfile

    Print log file lines that have not been read.

    Options:
      -h, --help            show this help message and exit
      -o OFFSET_FILE, --offset-file=OFFSET_FILE
                            File to which offset data is written (default:
                            <logfile>.offset).
      -p, --paranoid        Update the offset file every time we read a line 
                            (as opposed to only when we reach the end of the
                            file).
      -f, --follow          Do not exit at the end of the file, but wait for
                            new lines to be written.

In your code:

```python
from pygtail import Pygtail

for line in Pygtail("some.log"):
    sys.stdout.write(line)
```

Notes
-----

Pygtail does not handle rotated logs that have been compressed. You should
configure your log rotation script so that the most recently rotated log is
left uncompressed (`logrotated`, for example, has a `delaycompress` option
that does just that).

The "following" feature is implemented using one-second sleeps, as it was the
case with `tail -f` before coreutils 7.5. An extension to inotify would be nice.

Build status
------------

[![Build Status](https://secure.travis-ci.org/bgreenlee/pygtail.png)](http://travis-ci.org/bgreenlee/pygtail)


