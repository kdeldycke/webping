#!/usr/local/bin/python2.4
# -*- coding: utf-8 -*-

############################ START OF USER CONFIG ############################

CHECK_LIST = []

# The filepath of the report we want to produce.
# Can be an absolute file system path like /var/www/WebPing/index.html
# or a relative path from this script location.
DESTINATION_REPORT_FILE = "index.html"

# Configuration of the SMTP mail server
MAIL_SERVER  = "localhost"
# Identity under which we're sending mail alerts
FROM_ADDRESS = "WebPing <webping@example.com>"
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
import StringIO
import gzip
import smtplib
from os.path        import abspath
from urlparse       import urlparse
from email.MIMEText import MIMEText

# HTML safe
getSafeString = lambda s: ('%s' % s).replace('<', '&lt;').replace('>', '&gt;')

# HTML right padding
PAD = 3
padNumber = lambda value: "%s%d" % ((PAD - len(str(value))) * '&ensp;', value)

result_list = []
# Last night the urllib2 Missing Manual saved my life: http://www.voidspace.org.uk/python/articles/urllib2.shtml
socket.setdefaulttimeout(TIMEOUT)
# Display and process items by URLs
delProtocol = lambda c: ''.join(list(urlparse(c['url'])[1:]))
CHECK_LIST.sort(lambda a, b: cmp(delProtocol(a), delProtocol(b)))
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
  # Beautify URL
  result['url_msg'] = """<span class="protocol">%s://</span><span class="domain">%s</span><span class="url-trail">%s%s%s%s</span>""" % urlparse(check['url'])
  # Get time data
  result['update_time'] = datetime.datetime.now(TIMEZONE).isoformat(' ')
  result['update_msg']  = datetime.datetime.now(TIMEZONE).strftime(DATETIME_FORMAT)
  # Get the page and start the analysis to guess state
  try:
    fetcher = urllib2.urlopen(check['url'])
    fetcher.addheaders = [{'User-agent'     : "WebPing"
                         , 'Referer'        : "http://intranet.example.com:82"
                         , 'Accept-encoding': 'gzip'
                         }]
    page_content = fetcher.read()
    # Decode page content
    # Source: http://www.diveintopython.org/http_web_services/gzip_compression.html
    encoding = fetcher.headers.get('content-encoding', None)
    if encoding == 'gzip':
      page_content = gzip.GzipFile(fileobj = StringIO.StringIO(page_content)).read()
    elif encoding != None:
      result['state'] = 'fail'
      result['status_msg'] = "Unsupported encoding"
      # Proceed to next item
      result_list.append(result)
      continue
    # TODO: Convert character encoding to unicode
    # Source: http://stackoverflow.com/questions/1407874/python-urllib-minidom-and-parsing-international-characters/1408052#1408052
    # charset = fetcher.headers.get('content-type', None).split('charset=')[1]
    # page_content.decode(charset).encode('utf-8')
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
      result['state'] = 'warning'
      result['status_msg'] = "Page fetched but string not found"
      result_list.append(result)
      continue
    # Everything's OK
    result['state'] = 'ok'
    result['status_msg'] = "String found at given URL"
  # Compile a list of results
  result_list.append(result)

# Pre-compute some stats
total_count     = len(result_list)
fail_count      = len([r for r in result_list if r['state'] == 'fail'     ])
warning_count   = len([r for r in result_list if r['state'] == 'warning'  ])
ok_count        = len([r for r in result_list if r['state'] == 'ok'       ])
unchecked_count = len([r for r in result_list if r['state'] == 'unchecked'])

# Sort mail for beautiful display
MAILING_LIST.sort()
# As soon as we're done with data gathering, send alerts by mail if something is wrong
if fail_count > 0 or warning_count > 0:
  # Generate mail message header
  mail_template = """WebPing has detected:
  * %s failures
  * %s warnings

""" % ( fail_count
      , warning_count
      )
  # Display failures first then warnings
  for status in ['fail', 'warning']:
    for result in [i for i in result_list if i['state'] == status]:
      mail_template += """URL: %(url)s
  * Status         : %(state)s
  * Error message  : %(status_msg)s
  * String searched: %(str)s
  * Check time     : %(update_msg)s

""" % result
  # Generate mail message footer
  mail_template += """Mail alert generated at %s""" % datetime.datetime.now(TIMEZONE).strftime(DATETIME_FORMAT)
  # Generate the mail content
  mail_msg = MIMEText(mail_template)
  mail_msg['From'] = FROM_ADDRESS
  mail_msg['Subject'] = "[WebPing] Alert: %s" % ', '.join([s for s in [fail_count and "%s failures" % fail_count or None, warning_count and "%s warnings" % warning_count or None] if s])
  mail_msg['To'] = ', '.join(MAILING_LIST)
  # Temporarily increase socket timeout to contact mail server
  socket.setdefaulttimeout(60)
  # Connect to server and send the mail alert
  mail_server = smtplib.SMTP(MAIL_SERVER)
  mail_server.sendmail(FROM_ADDRESS, MAILING_LIST, mail_msg.as_string())
  mail_server.close()
  # Set back to a more reasonable time out
  socket.setdefaulttimeout(TIMEOUT)

# Produce a nice HTML report ready to be published by Apache
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

      a {text-decoration: none}
      a:hover {text-decoration: underline}

      abbr {
        cursor: help;
        border-bottom-width: 0;
      }

      .column {
        float: left;
        padding: 0 40px;
      }
      .c1 {border-right: 1px dotted #ccc}

      ul.center-aligned {list-style-type: none}
      ul span {font-weight: bold}
      ul .fail      {color: #e13737}
      ul .warning   {color: #ff7c00}
      ul .ok        {color: #0ab006}
      ul .unchecked {color: #ccc}

      table {
        border-collapse: collapse;
        border-left: 1px solid #686868;
        border-right: 1px solid #686868;
        text-align: left;
        clear: both;
        margin: 20px 0 0;
      }
      table tr {border: 1px solid #686868}
      table caption, table th           {font-weight: bold}
      table caption, table th, table td {padding: 4px 10px}
      table a .protocol  {color: #999}
      table a .domain    {font-weight: bold}
      table a .url-trail {font-size: .7em}
      table .empty_string {color: #999; font-style: italic}
      table .fail      {background-color: #e13737; color: #fff}
      table .warning   {background-color: #ff7c00; color: #fff}
      table .ok        {background-color: #0ab006; color: #fff}
      table .unchecked {background-color: #ccc;    color: #000}
    -->
    </style>
  </head>
  <body>
"""

body = """
    <h1>WebPing dashboard</h1>

    <div class="column c1">
      <p><strong>Summary</strong>:</p>
      <ul class="center-aligned">
        <li><span>%(total)s</span> sites monitored</li>
        <li><span class="fail">%(fail)s</span> error</li>
        <li><span class="warning">%(warning)s</span> warning</li>
        <li><span class="ok">%(ok)s</span> ok</li>
        <li><span class="unchecked">%(unchecked)s</span> unchecked</li>
      </ul>
    </div>
    
    <div class="column c2">
      <p><strong>People receiving mail alerts</strong>:</p>
      <ul>""" % { 'total'    : padNumber(total_count)
                , 'fail'     : padNumber(fail_count)
                , 'warning'  : padNumber(warning_count)
                , 'ok'       : padNumber(ok_count)
                , 'unchecked': padNumber(unchecked_count)
                }

body += '\n'.join(["<li>%s</li>" % email for email in MAILING_LIST])

body += """
      </ul>
    </div>

    <table>
      <thead>
        <tr>
          <th>URL to check</th>
          <th>String to search</th>
          <th>Status</th>
          <th>Last check</th>
        </tr>
      </thead>
      <tbody>"""

body += '\n'.join(["""
        <tr>
          <td><a href="%(url)s">%(url_msg)s</a></td>
          <td class="%(str_class)s">%(str_msg)s</td>
          <td class="%(state)s">%(status_msg)s</td>
          <td class="time"><abbr title="%(update_time)s">%(update_msg)s</abbr></td>
        </tr>""" % i for i in result_list])

body += """
      </tbody>
    </table>"""

footer = """
    <p>HTML report generated at %s</p>
  </body>
</html>""" % datetime.datetime.now(TIMEZONE).strftime(DATETIME_FORMAT)

html_report = open(abspath(DESTINATION_REPORT_FILE), 'w')
html_report.write(header + body + footer)
html_report.close()
