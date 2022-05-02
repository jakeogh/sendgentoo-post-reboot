# -*- coding: utf-8 -*-

import sys
import fastentrypoints
from setuptools import find_packages, setup
if not sys.version_info[0] == 3:
    sys.exit("Python 3 is required. Use: \'python3 setup.py install\'")

dependencies = ["icecream", "click"]

config = {
    "version": "0.1",
    "name": "sendgentoo_post_reboot",
    "url": "https://github.com/jakeogh/sendgentoo-post-reboot",
    "license": "ISC",
    "author": "Justin Keogh",
    "author_email": "github.com@v6y.net",
    "description": "takes a minimal sendgentoo install to my setup",
    "long_description": __doc__,
    "packages": find_packages(exclude=['tests']),
    "package_data": {"sendgentoo_post_reboot": ['py.typed']},
    "include_package_data": True,
    "zip_safe": False,
    "platforms": "any",
    "install_requires": dependencies,
    "entry_points": {
        "console_scripts": [
            "sendgentoo-post-reboot=sendgentoo_post_reboot.sendgentoo_post_reboot:cli",
        ],
    },
}

setup(**config)