import os
import unittest
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


def main():
    unittest.main()


if __name__ == "__main__":
    main()
