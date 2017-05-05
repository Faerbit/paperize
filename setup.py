import subprocess
from setuptools import setup, find_packages
from codecs import open
from os import path
import re

here = path.abspath(path.dirname(__file__))
readme = path.join(here, 'README.md')

# Convert the README to reStructuredText for PyPI if pandoc is available.
# Otherwise, just read it.
try:
    readme = subprocess.check_output(['pandoc', '-f', 'markdown',
        '-t', 'rst', readme]).decode('utf-8')
except:
    with open(readme, encoding='utf-8') as f:
        readme = f.read()

def version():
    from paperize.main import PAPERIZE_VERSION
    return PAPERIZE_VERSION


setup(
    name = 'paperize',
    version = version(),

    license = 'MIT',
    description = "Converts a binary file to printable QR codes and back",
    long_description = readme,
    url = 'https://github.com/faerbit/paperize',
    author = "Faerbit",
    author_email = 'faerbit at gmail dot com',
    classifiers = [
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
    ],

    packages = ['paperize'],
    install_requires = [
        'qrcode',
        'pypandoc',
    ],

    entry_points = {
        'console_scripts': [
            'paperize = paperize.main:main',
        ],
    },
)
