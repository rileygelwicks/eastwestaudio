try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension
    
import os
import sys
sys.path.insert(0, 'src')
from ewa import __version__ as version

description="an mp3 splicing system"
long_description="""
EWA (East-West Audio) is a server application that can
dynamically add intros and outros to mp3s based on user-defined
rules, so that podcasters can rotate promotional material included
in their mp3 downloads without remastering.
"""
platforms="OS Independent"

keywords=["mp3", "audio"]
classifiers=filter(None, """

Development Status :: 4 - Beta
Intended Audience :: System Administrators
Intended Audience :: Developers
Operating System :: OS Independent
Programming Language :: Python
Topic :: Multimedia :: Sound/Audio 
Topic :: Software Development :: Libraries :: Python Modules

""".split('\n'))

setup(author='Jacob Smullyan',
      author_email='jsmullyan@gmail.com',
      url='http://eastwestaudio.wnyc.org/',
      description=description,
      long_description=long_description,
      keywords=keywords,
      platforms=platforms,
      license='GPL',
      name='ewa',
      version=version,
      zip_safe=True,
      packages=['ewa', 'ewa.ply'],
      package_dir={'' : 'src'},
      test_suite='nose.collector',
      ext_modules=[Extension('ewa.frameinfo',
                             ['src/ewa/frameinfo.c'])],
      scripts=['bin/ewasplice',
               'bin/ewabatch',
               'bin/ewa'],
      install_requires=['eyeD3'],
      )
      
