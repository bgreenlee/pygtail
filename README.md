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
