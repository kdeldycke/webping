#!/usr/local/bin/python2.4
# -*- coding: utf-8 -*-

############################ START OF USER CONFIG ############################

# The filepath of the report we want to produce
DESTINATION_REPORT_FILE = "/var/tools/web-ping/index.html"

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
import StringIO
import gzip

# HTML safe
getSafeString = lambda s: ('%s' % s).replace('<', '&lt;').replace('>', '&gt;')

# HTML right padding
PAD = 3
padNumber = lambda value: "%s%d" % ((PAD - len(str(value))) * '&ensp;', value)

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
    charset = fetcher.headers.get('content-type', None).split('charset=')[1]
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

      abbr {
        cursor: help;
        border-bottom-width: 0;
      }

      ul {list-style-type: none}
      ul span {font-weight: bold}
      ul .unchecked {color: #ccc}
      ul .ok        {color: #0ab006}
      ul .warning   {color: #ff7c00}
      ul .fail      {color: #e13737}

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
      table .warning   {background-color: #ff7c00; color: #fff}
      table .fail      {background-color: #e13737; color: #fff}
    -->
    </style>
  </head>
  <body>
"""

body = """
    <h1>WebPing dashboard</h1>
    <p>Summary:
      <ul>
        <li><span>%(total)s</span> sites monitored</li>
        <li><span class="fail">%(fail)s</span> error</li>
        <li><span class="warning">%(warning)s</span> warning</li>
        <li><span class="ok">%(ok)s</span> ok</li>
        <li><span class="unchecked">%(unchecked)s</span> unchecked</li>
      </ul>
    </p>
    <table>
      <thead>
        <tr>
          <th>URL to check</th>
          <th>String to search</th>
          <th>Status</th>
          <th>Last check</th>
        </tr>
      </thead>
      <tbody>
""" % { 'total'    : padNumber(len(result_list))
      , 'unchecked': padNumber(len([r for r in result_list if r['state'] == 'unchecked']))
      , 'ok'       : padNumber(len([r for r in result_list if r['state'] == 'ok'       ]))
      , 'warning'  : padNumber(len([r for r in result_list if r['state'] == 'warning'  ]))
      , 'fail'     : padNumber(len([r for r in result_list if r['state'] == 'fail'     ]))
      }

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

html_report = open(DESTINATION_REPORT_FILE, 'w')
html_report.write(header + body + footer)
html_report.close()
