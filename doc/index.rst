============
 EWA Manual
============

:Author: Jacob Smullyan
:Contact: jsmullyan@gmail.com
:organization: WNYC New York Public Radio
:date: $Date$
:revision: $Revision$


.. :contents:: 
..
  1  Overview
  2  Deploying EWA
    2.1  Supported Platforms
    2.2  Software Installation
    2.3  The Managed Audio Directory
    2.4  Permissions Gotchas
    2.5  Configuration
      2.5.1  The ``ewa.conf`` File
      2.5.2  The EWA Rule Configuration File

Overview
========

what EWA is.


Deploying EWA
=============

Supported Platforms
-------------------

Ewa has been tested on Linux, but should work fine on any flavor of
BSD, including Mac OS X, and commercial UNIX implementations.  It
hasn't been tested on Windows, but might work there.  


Software Installation
---------------------

Ewa is written in `Python`_ and 

To install, if you already have setuptools installed, you can simply
do::

  easy_install ewa

Or, if you have already installed the source tarball and have unpacked
it, cd into it and type::

  easy_install .

or equivalently::

  python setup.py install

The latter will install setuptools if you don't already have it.



The Managed Audio Directory
---------------------------

Ewa expects audio to be stored in a directory structure like:

$basedir/main
	Your content mp3s go here; you manage this directory and can
	organize it however you like. Ewa needs read access to it.
$basedir/extras/masters
	Your "extra" files -- intros, outros, ads, etc. -- go here;
	you manage this directory also.  Ewa needs read access to it
	also. 
$basedir/extras/transcoded
	Ewa manages this directory and needs write access to it; it
	stores transcoded versions of the audio files extras/masters
	here. 
$targetdir
	Ewa manages this directory and needs write access to it; this
	is where it stores the spliced files.

``$basedir`` and ``$targetdir`` are configuration-defined.  You must
specify ``$basedir`` in ``ewa.conf``; ``$targetdir`` will default to
``$basedir/combined`` if not otherwise specified.


Permissions Gotchas
-------------------

Some care is necessary to ensure that file permissions will be right
for your deployment, especially if you are running both the ewa server
and ewa batch processes, as a variety of users may then be creating
files in the managed directories.  

One approach is to create a user and group that the ewa server will
run as, give ownership of the managed directories to it, and make them
both group-writeable and the group permissions sticky.  On Linux, you
might do this::

  groupadd ewa
  useradd -g ewa -s /bin/false  -d $targetdir -c "ewa user" ewa
  chown -r ewa:ewa $targetdir $basedir/extras/transcoded
  chmod -r g+ws $targetdir $basedir/extras/transcoded

While you are at it, creating directories for ewa's pid file and log
file aren't a bad idea::

  mkdir -p /var/{run,log}/ewa && chown ewa /var/{run,log}/ewa

In ``ewa.conf`` you'll want to set the ``user`` and ``group``
variables to match the user and group you created.  If you do this,
``ewa`` and ``ewabatch`` will need to be run as root (in the case of
``ewabatch``, most conveniently through ``sudo``), but will drop
credentials to your user/group before it creates any files.


Configuration
-------------

Ewa has two configuration files: ``ewa.conf``, for adminstrative
options, and a rule configuration file, which is used to determine
what the playlists.

The ``ewa.conf`` File
~~~~~~~~~~~~~~~~~~~~~

``ewa.conf`` is written in Python; keys defined there that don't start
with an underscore become attributes of the ``ewa.config.Config``
object.  The following values are provided by default:

* user
* group
* more ....

The following must be provided:

 basedir
     the root of the managed audio directory.

* rulefile -- 


The EWA Rule Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The rule file can be written in two formats:

* Python
* ewaconf


The most flexible option is Python; if you use this, the Python file
can contain anything as long as it defines a global with the name
"rules", which should be a ``Rule`` object (something that, when
called, returns an iterator that yields filenames relative to the
audioroot that will be merged).  With this hook you can load any sort
of rule system that you might like to devise.

If you want to use the default rule system, however, ewaconf is much
simpler.









