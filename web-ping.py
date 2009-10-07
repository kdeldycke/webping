#!/usr/local/bin/python2.4
# -*- coding: utf-8 -*-

"""
Setup steps:

  1. Create a cron config file:
       $ touch /etc/cron.d/web-ping

  2. Add in it the following configuration:
       0 * * * * www-data /usr/local/bin/python2.4 /var/tools/web-ping.py > /var/tools/web-ping-results.html

  3. Create a new config file for apache:
       $ touch /var/tools/web-ping.conf

  4. And add the following directives:
       Listen 82
       <VirtualHost intranet.example.com:82>
         DocumentRoot /var/tools/
         DirectoryIndex web-ping-results.html
         # Redirect any request to the default directory root index
         RewriteEngine on
         RewriteCond %{REQUEST_URI} !/web-ping-results.html$
         RewriteRule $ /web-ping-results.html [R=301,L]
       </VirtualHost>

  5. Then edit your main apache config:
       $ vi /var/httpd/httpd-2.2/conf/httpd.conf

  6. And add the following directive:
       Include /var/tools/web-ping.conf

"""

############################ START OF USER CONFIG ############################

CHECK_LIST = []

# TODO
# List of mails to send reports to
MAILING_LIST = []

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
# TODO
TIMEZONE = None

#Sockets timeout in seconds
TIMEOUT = 30

############################# END OF USER CONFIG #############################



import datetime
import socket
import urllib2
import sys

# HTML safe
getSafeString = lambda s: ('%s' % s).replace('<', '&lt;').replace('>', '&gt;')

result_list = []
# Last night the urllib2 Missing Manual saved my life: http://www.voidspace.org.uk/python/articles/urllib2.shtml
socket.setdefaulttimeout(TIMEOUT)
# Display and process items by URLs
CHECK_LIST.sort(lambda a, b: cmp(a['url'], b['url']))
for check in CHECK_LIST:
  # Init and normalize result items
  result = check.copy()
  result['state'] = 'unchecked'
  result['status_msg'] = "Unchecked"
  if not result.has_key('str') or not result['str'].strip():
    result['str_msg'] = "None"
    result['str'] = None
    result['str_class'] = 'empty_string'
  else:
    result['str_msg'] = "&#171;&nbsp;%s&nbsp;&#187;" % result['str']
    result['str_class'] = None
  result['update_time'] = datetime.datetime.now(TIMEZONE).isoformat(' ')
  result['update_msg']  = datetime.datetime.now(TIMEZONE).strftime(DATETIME_FORMAT)
  # Get the page and start the analysis to guess state
  try:
    fetcher = urllib2.urlopen(check['url'])
    fetcher.addheaders = [{'User-agent': "WebPing"
                         , 'Referer'   : "http://intranet.example.com:82"
                         }]
    page_content = fetcher.read()
  except urllib2.HTTPError:
    result['state'] = 'fail'
    result['status_msg'] = getSafeString(sys.exc_value)
    # Proceed to next item
    result_list.append(result)
    continue
  except urllib2.URLError, e:
    result['state'] = 'fail'
    # Try to print a useful error message
    if isinstance(e.reason, socket.timeout):
      result['status_msg'] = "Socket timed out after %s seconds" % TIMEOUT
    elif isinstance(e.reason, socket.error):
      result['status_msg'] = "Network Error %s: %s" % (e.reason[0], e.reason[1])
    else:
      result['status_msg'] = "Unknown error: %s " % getSafeString(sys.exc_value)
    # Proceed to next item
    result_list.append(result)
    continue
  # Look for a particular string
  if not result['str']:
    # No need to search a given string, if the page fetching hasn't failed yet, then it's a success ! :)
    result['state'] = 'ok'
    result['status_msg'] = "Page fetched successfuly"
  else:
    # Can't find the string
    if page_content.find(result['str']) == -1:
      result['state'] = 'dubious'
      result['status_msg'] = "Page fetched but string not found"
      result_list.append(result)
      continue
    # Everything's OK
    result['state'] = 'ok'
    result['status_msg'] = "String found at given URL"
  # Compile a list of results
  result_list.append(result)
  

# Print nice HTML
header = """
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <title>WebPing dashboard</title>
    <style type="text/css">
    <!--
      body {
        font-family: "Calibri", "Helvetica", "Verdana", "Arial", sans-serif;
        color: #333;
      }

      abbr {
        cursor: help;
        border-bottom-width: 0;
      }

      table {
        border-collapse: collapse;
        border-left: 1px solid #686868;
        border-right: 1px solid #686868;
        text-align: left;
      }
      table tr {
        border: 1px solid #686868;   
      }
      table caption, table th {
        font-weight: bold;
      }
      table caption, table th, table td {
        padding: 4px 10px;
      }
      table .empty_string {color: #999; font-style: italic}
      table .unchecked {background-color: #ccc;    color: #000}
      table .ok        {background-color: #0ab006; color: #fff}
      table .dubious   {background-color: #ff7c00; color: #fff}
      table .fail      {background-color: #e13737; color: #fff}
    -->
    </style>
  </head>
  <body>
"""

body = """
    <table>
      <caption>WebPing dashboard</caption>
      <thead>
        <tr>
          <th>URL to check</th>
          <th>String to search</th>
          <th>Status</th>
          <th>Last check</th>
        </tr>
      </thead>
      <tbody>
"""

body += '\n'.join(["""
        <tr>
          <td><a href="%(url)s">%(url)s</a></td>
          <td class="%(str_class)s">%(str_msg)s</td>
          <td class="%(state)s">%(status_msg)s</td>
          <td class="time"><abbr title="%(update_time)s">%(update_msg)s</abbr></td>
        </tr>
""" % i for i in result_list])

body += """
      </tbody>
    </table>
"""

footer = """
  </body>
</html>
"""

print header + body + footer
