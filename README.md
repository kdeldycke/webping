WebPing
=======

Description
-----------

WebPing is a tiny utility to check availability of remote web pages. It
produces an HTML report to show results. It can send mails alerts when a page
can't be reached. It also search for a given string in the page and calculate
page response time.

This is basically a stupid and simple script. It was created at EDF for the
very specific needs of the internal intranet team but can be used in other contexts.


Requirements
------------

 * a Python interpreter (tested with Python 2.4.x), to build and run WebPing.
 * an access to internet, to let buildout download its dependencies via PyPi.
 * a web server (tested with Apache 2.2.x), to serve generated HTML reports.
 * a cron-like software, to "tick" WebPing regularly.
 * SQLite > 3.x.


Install and Setup steps
-----------------------

This how-to is designed around our current internal use of WebPing.
Don't forget to adapt it to you needs and your environment.

1. Install required packages:

        $ sudo su
        $ yum install subversion gcc sqlite-devel python-devel

1. Check out the latest version of WebPing from our internal SVN repository:

        $ cd /var/www
        $ svn co svn://intranet.example.com:3690/project/WebPing/trunk WebPing

1. Fix rights and ownership (quick and dirty):

        $ chmod -R 755 ./WebPing
        $ chown -R www-data:www-data ./WebPing

1. Initialize the buildout environment:

        $ su - www-data
        $ cd /var/www/WebPing
        $ python ./bootstrap.py --distribute

1. Run buildout itself:

        $ ./bin/buildout

1. Setup the cron file:

        $ sudo echo "*/10 * * * * www-data /var/www/WebPing/bin/webping" > /etc/cron.d/webping

1. Register WebPing's specific web configuration to your Apache server:

        $ ln -s /var/www/WebPing/apache.conf /etc/apache/conf.d/
        $ /etc/init.d/apache stop
        $ /etc/init.d/apache start

1. Eventually change WebPing config file to match your needs:

        $ vi /var/www/WebPing/webping.conf


Troubleshooting
---------------

<dl>

  <dt>
    Step 3  of the install process above is stuck when running the
    bootstrap script, and/or return a connection timeout error.
  </dt>
  <dd>
    This may be due to your machine/user not having access to internet.
    Please carefully check your network/proxy configuration.
  </dd>

  <dt>
    Pages seems to be checked regularly but with a constant delay.
  </dt>
  <dd>
    Check that the ntp server is properly configured and running on the
    server side.
  </dd>

</dl>


Author
------

 * Kevin Deldycke <kevin@deldycke.com>


Contributors
------------

These people contributed code:

  * Matthieu Diehr <matthieu.diehr@gmail.com>


License
-------

WebPing is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, version 2.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

For full details, please see the file named COPYING in the top directory of the
source tree. You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.


Embedded external projects
--------------------------

WebPing uses external softwares, scripts, libraries and artworks:

        jQuery JavaScript Library v1.3.2
        Copyright (c) 2009 John Resig
        Dual licensed under the MIT and GPL licenses.
        Source: http://jquery.com

        jQuery.Flot plugin v0.6
        Copyright (c) 2007-2009 IOLA and Ole Laursen
        Released under the MIT license.
        Source: http://code.google.com/p/flot

        jQuery.cuteTime plugin v1.1.1
        Copyright (c) 2009 Jeremy Horn <jeremydhorn@gmail.com>, http://tpgblog.com
        Dual licensed under MIT and GPL.
        Source: http://tpgblog.com/cutetime

        ExplorerCanvas
        Copyright (c) 2006 Google Inc.
        Released under the Apache License 2.0.
        Source: http://code.google.com/p/explorercanvas

        Crystal Project Icons
        Copyright (c) 2006-2007, Everaldo Coelho <everaldo@everaldo.com>, http://www.everaldo.com
        Released under the LGPL license.
        Source: http://www.kde-look.org/content/show.php/Crystal+Project?content=60475

        Buildout's bootstrap.py
        Copyright (c) 2006 Zope Corporation and Contributors
        Distributed under the Zope Public License, version 2.1 (ZPL).
        Source: http://svn.zope.org/repos/main/zc.buildout/trunk/bootstrap/bootstrap.py
