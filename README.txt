pygtail
=======

A python "port" of `logcheck's logtail2 <http://logcheck.org>`__.

Pygtail reads log file lines that have not been read. It will even
handle log files that have been rotated.

Usage
-----

From the command line:

::

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
      -n N, --every-n=N     Update the offset file every N'th time we read a
                            line (as opposed to only when we reach the end of
                            the file).
      --no-copytruncate     Don't support copytruncate-style log rotation.
                            Instead, if the log file shrinks, print a warning.

In your code:

.. code:: python

    from pygtail import Pygtail

    for line in Pygtail("some.log"):
        sys.stdout.write(line)

Build status
------------

|Build Status|

.. |Build Status| image:: https://secure.travis-ci.org/bgreenlee/pygtail.png
   :target: http://travis-ci.org/bgreenlee/pygtail
