from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='Products.ZPerFactMods',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='',
      author_email='',
      url='',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      package_data={
          'Products.ZPerFactMods': ['www/*',]
      },
      include_package_data=True,
      zip_safe=False,
      namespace_packages=['Products'],
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
