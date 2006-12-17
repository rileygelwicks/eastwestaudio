import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, Extension
import os
import sys
sys.path.insert(0, 'src')
from ewa import __version__ as version

description="an mp3 splicing system"
platforms="OS Independent"

keywords=["mp3", "audio"]
classifiers=filter(None, """

Development Status :: 3 - Alpha
Intended Audience :: System Administrators
Intended Audience :: Developers
Operating System :: OS Independent
Programming Language :: Python
Topic :: Multimedia :: Sound/Audio 
Topic :: Software Development :: Libraries :: Python Modules

""".split('\n'))

setup(author='Jacob Smullyan',
      author_email='jsmullyan@gmail.com',
      description=description,
      keywords=keywords,
      platforms=platforms,
      license='GPL',
      name='ewa',
      version=version,
      zip_safe=True,
      packages=['ewa'],
      package_dir={'' : 'src'},
      ext_modules=[Extension('ewa.frameinfo',
                             ['src/ewa/frameinfo.c'])],
      scripts=['bin/ewasplice',
               'bin/ewabatch',
               'bin/ewa'],
##       install_requires=['ply >=2.2',
##                         'eyeD3',
##                         'setuptools',
##                         'simplejson >=1.3']
      )
      
