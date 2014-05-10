import os
import sys
import unittest
import shutil
import tempfile
from pygtail import Pygtail


class PygtailTest(unittest.TestCase):
    # TODO:
    # - test for non-default offset file
    # - test for paranoid flag
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
        for tmpfile in [filename, filename + ".offset", filename + ".1"]:
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

    def test_logrotate(self):
        new_lines = ["4\n5\n", "6\n7\n"]
        pygtail = Pygtail(self.logfile.name)
        pygtail.read()
        self.append(new_lines[0])
        os.rename(self.logfile.name, "%s.1" % self.logfile.name)
        self.append(new_lines[1])
        pygtail = Pygtail(self.logfile.name)
        self.assertEqual(pygtail.read(), ''.join(new_lines))

    def test_copytruncate_off_smaller(self):
        self.test_readlines()
        self.copytruncate()
        new_lines = "4\n5\n"
        self.append(new_lines)
        pygtail = Pygtail(self.logfile.name, copytruncate=False)
        self.assertEqual(pygtail.read(), None)
        self.assertRegexpMatches(sys.stderr.getvalue(), r".*?\bWARN\b.*?\bshrank\b.*")

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


def main():
    unittest.main(buffer=True)


if __name__ == "__main__":
    main()
