#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'StarFlow',
    version = '0.9999',
    packages = ['starflow', 'starflow.commands', 'starflow.tests'],
    package_dir = {'starflow':'starflow'},
    scripts=['bin/starflow',],

    install_requires=[
        "tabular",
        "networkx",
        "numpy>=1.3",
    ],

    zip_safe = True,

    author='Daniel Yamins',
    author_email='dyamins@gmail.com',
    url="http://web.mit.edu/star/flow",
    description="StarFlow is....",
    long_description = """
    StarFlow is really...
    """,

    download_url='http://web.mit.edu/stardev/flow',
    license='LGPL3',

    classifiers=[
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing',
    ],
)
