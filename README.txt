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

 * a Python interpreter (tested with Python 2.4.x)
 * a web server (tested with Apache 2.2.x)
 * a cron-like software


Install and Setup steps
-----------------------

This how-to is designed around our current internal use of WebPing.
Don't forget to adapt it to you needs and your environment.

  1. Check out the latest version of WebPing from our internal SVN repository:
       $ sudo su
       $ cd /var/www
       $ svn co http://intranet.example.com:3690/project/WebPing/trunk WebPing

  2. Fix rights and ownership (quick and dirty):
       $ chmod -R 755 /var/www/WebPing
       $ chown -R www-data:www-data /var/www/WebPing

  3. Create a cron file:
       $ touch /etc/cron.d/web-ping

  4. Add in it the following configuration:
       */10 * * * * www-data /usr/local/bin/python2.4 /var/www/WebPing/web-ping.py

  5. Then edit your main apache config:
       $ vi /var/httpd/httpd-2.2/conf/httpd.conf

  6. And add the following directive:
       Include /var/www/WebPing/apache.conf

  7. Eventually change WebPing config file to match your needs:
       $ vi /var/www/WebPing/web-ping.conf


Troubleshooting
---------------

Problem:  Pages seems to be checked regularly but with a constant delay.
Solution: Check that the ntp server is properly configured and running on the
          server side.


Author
------

 * Kevin Deldycke <kevin@deldycke.com>


Contributors
------------
 


 * Matthieu Diehr <matthieu.diehr@gmail.com>


Embedded external projects
--------------------------

WebPing uses external softwares, scripts, libraries and artworks:
  
  jQuery JavaScript Library v1.3.2
  Copyright (c) 2009 John Resig
  Dual licensed under the MIT and GPL licenses.
  Source: http://jquery.com

  jQuery.cuteTime plugin v1.1.1
  Copyright (c) 2009 Jeremy Horn <jeremydhorn@gmail.com>, http://tpgblog.com	
  Dual licensed under MIT and GPL.
  Source: http://tpgblog.com/cutetime

  Crystal Project Icons
  Copyright (c) 2006-2007, Everaldo Coelho <everaldo@everaldo.com>, http://www.everaldo.com
  Released under the LGPL licence.
  Source: http://www.kde-look.org/content/show.php/Crystal+Project?content=60475

  Buildout's bootstrap.py
  Copyright (c) 2006 Zope Corporation and Contributors
  Distributed under the Zope Public License, version 2.1 (ZPL).
  Source: http://svn.zope.org/*checkout*/zc.buildout/trunk/bootstrap/bootstrap.py

  MySQL 5.1.44 source code
  Copyright (c) Sun Microsystems, Inc.
  Distributed under the GPLv2 licence.
  Source: http://dev.mysql.com/get/Downloads/MySQL-5.1/mysql-5.1.44.tar.gz/from/http://mirrors.ircam.fr/pub/mysql/
