"""Legacy packaging for the Axolotl Python 2.7 migration fixture."""
from setuptools import setup

setup(
    name='local-chess',
    version='2.0.0',
    description='Two-player local chess for the console (Python 2.7 fixture)',
    packages=['local_chess'],
    python_requires='>=2.7,<3',
    entry_points={'console_scripts': ['local-chess=local_chess.__main__:main']},
    classifiers=['Programming Language :: Python :: 2.7'],
)
