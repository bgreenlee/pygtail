import os
import sys

try:
    # python 2.6
    import unittest2 as unittest
except ImportError:
    import unittest
import shutil
import tempfile
import gzip
import io
try:
    from pygtail import Pygtail
except Exception:
    sys.path.insert(0,'..')
    from pygtail import Pygtail

PY2 = sys.version_info[0] == 2


class PygtailTest(unittest.TestCase):
    # TODO:
    # - test for non-default offset file
    # - test for savelog and datext rotation schemes

    def setUp(self):
        self.test_lines = ["1\n", "2\n", "3\n"]
        self.test_str = ''.join(self.test_lines)
        self.logfile = tempfile.NamedTemporaryFile(delete=False)
        self.logfile.write(self.test_str.encode('utf-8'))
        self.logfile.close()

    def append(self, str):
        # append the give string to the temp logfile
        fh = open(self.logfile.name, "a")
        fh.write(str)
        fh.close()

    def copytruncate(self):
        shutil.copyfile(self.logfile.name, "%s.1" % self.logfile.name)
        fh = open(self.logfile.name, "w")
        fh.close()

    def tearDown(self):
        filename = self.logfile.name
        for tmpfile in [filename, filename + ".offset", filename + ".1", filename + ".1.gz"]:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)

    def test_read(self):
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), self.test_str)

    def test_readlines(self):
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.readlines(), self.test_lines)

    def test_subsequent_read_with_no_new_data(self):
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), self.test_str)
        self.assertEqual(pygtail.read(), None)

    def test_subsequent_read_with_new_data(self):
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), self.test_str)
        new_lines = "4\n5\n"
        self.append(new_lines)
        new_pygtail = Pygtail(self.logfile.name)
        self.assertEqual(new_pygtail.read(), new_lines)

    def test_read_from_the_file_end(self):
        pygtail = Pygtail(self.logfile.name, read_from_end=True)
        self.assertEqual(pygtail.read(), None)
        new_lines = "4\n5\n"
        self.append(new_lines)
        new_pygtail = Pygtail(self.logfile.name, read_from_end=True)
        self.assertEqual(new_pygtail.read(), new_lines)

    def test_logrotate_without_delay_compress(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])

        # put content to gzip file
        gzip_handle = gzip.open("%s.1.gz" % self.logfile.name, 'wb')
        with open(self.logfile.name, 'rb') as logfile:
            gzip_handle.write(logfile.read())
        gzip_handle.close()

        with open(self.logfile.name, 'w'):
            # truncate file
            pass

        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_logrotate_with_delay_compress(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])
        os.rename(self.logfile.name, "%s.1" % self.logfile.name)
        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_logrotate_with_dateext_with_delaycompress(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])
        os.rename(self.logfile.name, "%s-20160616" % self.logfile.name)
        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_logrotate_with_dateext_without_delaycompress(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])

        # put content to gzip file
        gzip_handle = gzip.open("%s-20160616.gz" % self.logfile.name, 'wb')
        with open(self.logfile.name, 'rb') as logfile:
            gzip_handle.write(logfile.read())
        gzip_handle.close()

        with open(self.logfile.name, 'w'):
            # truncate file
            pass

        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_logrotate_with_dateext2_with_delaycompress(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])
        os.rename(self.logfile.name, "%s-20160616-1466093571" % self.logfile.name)
        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_logrotate_with_dateext2_without_delaycompress(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])

        # put content to gzip file
        gzip_handle = gzip.open("%s-20160616-1466093571.gz" % self.logfile.name, 'wb')
        with open(self.logfile.name, 'rb') as logfile:
            gzip_handle.write(logfile.read())
        gzip_handle.close()

        with open(self.logfile.name, 'w'):
            # truncate file
            pass

        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_timed_rotating_file_handler(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])
        os.rename(self.logfile.name, "%s.2016-06-16" % self.logfile.name)
        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_custom_rotating_file_handler_with_prepend(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])
        file_dir, rel_filename = os.path.split(self.logfile.name)
        os.rename(self.logfile.name, os.path.join(file_dir, "custom_log_pattern.%s" % rel_filename))
        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name, log_patterns=["custom_log_pattern.%s"])
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_copytruncate_off_smaller(self):
        self.test_readlines()
        self.copytruncate()
        new_lines = "4\n5\n"
        self.append(new_lines)

        sys.stderr = captured = io.BytesIO() if PY2 else io.StringIO()
        pygtail = Pygtail(self.logfile.name, copytruncate=False)
        captured_value = captured.getvalue()
        sys.stderr = sys.__stderr__

        assert_class = self.assertRegex if sys.version_info >= (3, 1) else self.assertRegexpMatches
        assert_class(captured_value, r".*?\bWARN\b.*?\bshrank\b.*")
        self.assertEqual(pygtail.read(), None)

    def test_copytruncate_on_smaller(self):
        self.test_readlines()
        self.copytruncate()
        new_lines = "4\n5\n"
        self.append(new_lines)
        pygtail = Pygtail(self.logfile.name, copytruncate=True)
        self.assertEqual(pygtail.read(), new_lines)

    def _test_copytruncate_larger(self, onoff):
        self.test_readlines()
        self.copytruncate()
        self.append(self.test_str)
        new_lines = "4\n5\n"
        self.append(new_lines)
        pygtail = Pygtail(self.logfile.name, copytruncate=onoff)
        self.assertEqual(pygtail.read(), new_lines)

    def test_copytruncate_larger_off(self):
        self._test_copytruncate_larger(False)

    def test_copytruncate_larger_on(self):
        self._test_copytruncate_larger(True)

    def test_offset_file(self):
        pygtail = Pygtail(self.logfile.name, paranoid=True)

        log_inode = os.stat(self.logfile.name).st_ino

        next(pygtail)
        with open(self.logfile.name + '.offset', 'r') as f:
            inode, offset = int(next(f)), int(next(f))
        self.assertEqual(inode, log_inode)
        self.assertEqual(offset, 2)

        next(pygtail)
        with open(self.logfile.name + '.offset', 'r') as f:
            inode, offset = int(next(f)), int(next(f))
        self.assertEqual(inode, log_inode)
        self.assertEqual(offset, 4)

        next(pygtail)
        with open(self.logfile.name + '.offset', 'r') as f:
            inode, offset = int(next(f)), int(next(f))
        self.assertEqual(inode, log_inode)
        self.assertEqual(offset, 6)

    def test_on_update_with_paranoid(self):
        updates = [0]

        def record_update():
            updates[0] += 1

        pygtail = Pygtail(self.logfile.name, paranoid=True,
                          on_update=record_update)

        self.assertEqual(updates[0], 0)
        next(pygtail)
        self.assertEqual(updates[0], 1)
        next(pygtail)
        self.assertEqual(updates[0], 2)
        next(pygtail)
        self.assertEqual(updates[0], 3)

    def test_on_update_without_paranoid(self):
        updates = [0]

        def record_update():
            updates[0] += 1

        pygtail = Pygtail(self.logfile.name, on_update=record_update)

        self.assertEqual(updates[0], 0)
        for line in pygtail:
            self.assertEqual(updates[0], 0)
        self.assertEqual(updates[0], 1)

    def test_every_n(self):
        updates = [0]
        # We save before returning the second line.
        # We save at the end of the file with all 3 recorded.
        expected = [1, 3]
        previous_lines = 0

        def record_update():
            self.assertEqual(previous_lines, expected[updates[0]])
            updates[0] += 1

        pygtail = Pygtail(self.logfile.name, every_n=2, on_update=record_update)

        self.assertEqual(updates[0], 0)
        for line in pygtail:
            previous_lines += 1

    def test_renamecreate(self):
        """
        Tests "renamecreate" semantics where the currently processed file gets renamed and the
        original file gets recreated. This is the behavior of certain logfile rollers such as
        TimeBasedRollingPolicy in Java's Logback library.
        """
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        os.rename(self.logfile.name, "%s.2018-03-10" % self.logfile.name)
        # append will recreate the original log file
        self.append(new_lines[0])
        self.append(new_lines[1])
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_full_lines(self):
        """
        Tests lines are logged only when they have a new line at the end. This is useful to ensure that log lines
        aren't unintentionally split up.
        """
        pygtail = Pygtail(self.logfile.name, full_lines=True)
        new_lines = "4\n5,"
        last_line = "5.5\n6\n"

        self.append(new_lines)
        pygtail.read()
        self.append(last_line)
        self.assertEqual(pygtail.read(), "5,5.5\n6\n")


def main():
    unittest.main(buffer=True)


if __name__ == "__main__":
    main()
