# -*- coding: utf-8 -*-
# Copyright (c) 2012  Infrae. All rights reserved.
# See also LICENSE.txt
from setuptools import setup, find_packages
import os

version = '3.0c1'

tests_require = [
    'Products.Silva [test]',
    'infrae.testing',
    ]

setup(name='silva.core.upgrade',
      version=version,
      description="Generic upgrade functions used in Silva",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Framework :: Zope2",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: BSD License",
        ],
      keywords='silva core upgrade',
      author='Sylvain Viollon',
      author_email='info@infrae.com',
      url='http://infrae.com/products/silva',
      license='BSD',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      namespace_packages=['silva'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'martian',
          'five.grok',
          'five.localsitemanager',
          'grokcore.site',
          'silva.core.interfaces',
          'silva.core.services',
          'silva.system.utils',
          'zope.annotation',
          'zope.interface',
          'zope.component',
          ],
      tests_require = tests_require,
      extras_require = {'test': tests_require},
      entry_points = """
      [zodbupdate]
      renames = silva.core.upgrade:CLASS_CHANGES
      [silva.system.utils]
      upgrade = silva.core.upgrade.command:UpgradeCommand
      """
      )
