from distutils.core import setup

from setuptools import find_packages

import superloops

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='superloops',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests", "examples", "docs", "out", "dist"]),
    version=superloops.__version__,
    license='Apache-2.0',
    description='SuperLoops package simplifies and augments usage of Python threads. It provides support for thread maintenance, events, failure handling, health status propagation, and graceful termination.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Voy Zan',
    author_email='voy1982@yahoo.co.uk',
    url='https://github.com/Voyz/superloops',
    keywords=['thread', 'threads', 'python threads', 'threading', 'multithreading', 'asynchronous', 'concurrency', 'thread management'],
    classifiers=[
        'Development Status :: 4 - Beta',
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.6',
    ],
)
