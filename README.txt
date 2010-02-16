Description
-----------

WebPing is a tiny utility to check availability of remote web pages. It
produces an HTML report to show results. It can send mails alerts when a page
can't be reached. It also search for a given string in the page and calculate
page response time.

This is basically a stupid and simple script. It was created at EDF for the
needs of the internal intranet team but can be used in other contexts.


Requirements
------------

 * a Python interpreter (tested with Python 2.4.6)
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


Author
------

 * Kevin Deldycke <kevin@deldycke.com>


Contributors
------------
 


 * Matthieu Diehr <matthieu.diehr@gmail.com>

