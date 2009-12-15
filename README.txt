Setup steps
-----------

  1. Create a cron config file:
       $ touch /etc/cron.d/web-ping

  2. Add in it the following configuration:
       */10 * * * * root /usr/local/bin/python2.4 /var/www/WebPing/web-ping.py

  3. Edit WebPing's apache configuration to adjust parameters if necessary:
       $ vi /var/www/WebPing/web-ping.conf

  4. Then edit your main apache config:
       $ vi /var/httpd/httpd-2.2/conf/httpd.conf

  5. And add the following directive:
       Include /var/www/WebPing/web-ping.conf
