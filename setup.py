from setuptools import setup, find_packages
import os

version = '2.2dev'

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
      packages=find_packages(exclude=['ez_setup']),
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
          'zope.annotation',
          'zope.interface',
          'zope.component',
          ],
      entry_points = """
      [zodbupdate]
      renames = silva.core.upgrade:CLASS_CHANGES
      """
      )
