"""
ewa splices MP3s according to rules.
"""
import os
if not os.environ.get('PYTHONSETUP'):
    from ewa.mp3 import *
    from ewa.logutil import *
    from ewa.rules import *
    from ewa.audio import *
del os
__version__='0.62'
__author__='Jacob Smullyan'
__license__='GPL'

