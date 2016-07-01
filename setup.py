import os
from setuptools import setup

from pygtail import __version__


def main():
    cwd = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(cwd, 'README.txt')
    readme = open(path, 'r').read()

    setup(
        name = 'pygtail',
        version = __version__,
        description = 'Reads log file lines that have not been read.',
        license = 'GPL v2',
        author = 'Brad Greenlee',
        author_email = 'brad@footle.org',
        keywords = ['logging', 'tail', 'logtail2'],
        url = 'http://github.com/bgreenlee/pygtail',
        packages = ['pygtail'],
        entry_points = {
            'console_scripts': ['pygtail=pygtail.core:main']
            },
        test_suite='pygtail.test',
        classifiers = [
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU General Public License (GPL)",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: POSIX :: Linux",
            "Operating System :: Unix",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2.6",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: System :: Logging"
            ],
        long_description = readme
        )


if __name__ == '__main__':
    main()
