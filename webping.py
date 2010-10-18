#!/usr/local/bin/python2.4
# -*- coding: utf-8 -*-

# Current WebPing version
__version__ = '0.2.dev'


import md5
import sys
import gzip
import time
import yaml
import getopt
import socket
import os.path
import smtplib
import urllib2
import datetime
import StringIO
from urlparse       import urlparse
from pysqlite2      import dbapi2 as sqlite
from email.MIMEText import MIMEText


# Date format we feed to jquery.cuteTime
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Set default config file location
DEFAULT_CONF = 'webping.conf'
# File name of the database
DB_NAME = "webping.sqlite"
TABLE_NAME = "webping"


def webping(config_path):
  script_folder = os.path.dirname(os.path.abspath(__file__))

  # Load config file
  if not os.path.isabs(config_path):
    config_path = os.path.abspath(os.path.join(script_folder, config_path))
  config_file = file(config_path, 'r')
  conf = yaml.load(config_file)

  # Open the database and create one if not available
  db_path = os.path.abspath(os.path.join(script_folder, DB_NAME))
  db = sqlite.connect(db_path)
  table_list = [t[0] for t in db.execute("SELECT tbl_name FROM sqlite_master")]
  if TABLE_NAME not in table_list:
    db.execute("""CREATE TABLE %s ( url           TEXT
                                  , string        TEXT
                                  , status        TEXT
                                  , check_time    TEXT
                                  , response_time REAL
                                  )""" % TABLE_NAME)

  # HTML safe
  getSafeString = lambda s: ('%s' % s).replace('<', '&lt;').replace('>', '&gt;')

  # HTML right padding
  PAD = 3
  padNumber = lambda value: "%s%d" % ((PAD - len(str(value))) * '&ensp;', value)

  result_list = []
  # Last night the urllib2 Missing Manual saved my life: http://www.voidspace.org.uk/python/articles/urllib2.shtml
  socket.setdefaulttimeout(conf['TIMEOUT'])
  # Display and process items by URLs
  delProtocol = lambda c: ''.join(list(urlparse(c['url'])[1:]))
  conf['CHECK_LIST'].sort(lambda a, b: cmp(delProtocol(a), delProtocol(b)))
  for check in conf['CHECK_LIST']:
    # Init and normalize result items
    result = check.copy()
    result['state'] = 'unchecked'
    result['status_msg'] = "Unchecked"
    result['response_time'] = None
    result['response_time_msg'] = "undetermined"
    result['response_time_class'] = "unknown"
    if not result.has_key('str') or not result['str'].strip():
      result['str_msg'] = "none"
      result['str'] = None
      result['str_class'] = 'empty_string'
    else:
      result['str_msg'] = "&#171;&nbsp;%s&nbsp;&#187;" % result['str']
      result['str_class'] = None
    # Beautify URL
    result['url_msg'] = """<span class="protocol">%s://</span><span class="domain">%s</span><span class="url-trail">%s%s%s%s</span>""" % urlparse(check['url'])
    # Get time data
    check_time = datetime.datetime.now(conf['TIMEZONE'])
    result['update_time'] = check_time.isoformat(' ')
    result['update_msg']  = check_time.strftime(DATETIME_FORMAT)
    # Get the page and start the analysis to guess state
    try:
      req = urllib2.Request(check['url'])
      req.add_header('User-agent'     , "WebPing")
      req.add_header('Referer'        , "http://intranet.example.com:82")
      req.add_header('Accept-encoding', 'gzip')
      start_time = datetime.datetime.now()
      fetcher = urllib2.urlopen(req)
      end_time = datetime.datetime.now()
      response_time = end_time - start_time
      response_time = (response_time.days * 24 * 60 * 60) + response_time.seconds + (response_time.microseconds / 1000000.0)
      result['response_time'] = response_time
      result['response_time_msg'] = "%.3f s." % response_time
      if response_time >= conf['RESPONSE_TIME_THRESHOLD']:
        result['response_time_class'] = "slow"
      else:
        result['response_time_class'] = "acceptable"
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
        result['status_msg'] = "Socket timed out after %s seconds" % conf['TIMEOUT']
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

  # Populate the database with our fresh datas
  db.executemany("""INSERT INTO %s (url     , string  , status    , check_time      , response_time     )
                            VALUES (?       , ?       , ?         , ?               , ?                 )""" % TABLE_NAME
                ,                 [(d['url'], d['str'], d['state'], d['update_time'], d['response_time']) for d in result_list]
                )

  # End of the data collecting phase, commit our changes in the database
  db.commit()

  # Pre-compute some stats
  total_count     = len(result_list)
  fail_count      = len([r for r in result_list if r['state'] == 'fail'     ])
  warning_count   = len([r for r in result_list if r['state'] == 'warning'  ])
  ok_count        = len([r for r in result_list if r['state'] == 'ok'       ])
  unchecked_count = len([r for r in result_list if r['state'] == 'unchecked'])

  # Determine global status icon
  global_status_icon = "down.png"
  if fail_count > 0:
    global_status_icon = "minimum.png"
  elif warning_count > 0:
    global_status_icon = "good.png"
  elif unchecked_count == total_count:
    global_status_icon = "offline.png"
  elif unchecked_count + ok_count == total_count:
    global_status_icon = "excellent.png"

  # Sort mail for beautiful display
  conf['MAILING_LIST'].sort()
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
    mail_template += """Mail alert generated at %s""" % datetime.datetime.now(conf['TIMEZONE']).strftime(DATETIME_FORMAT)
    # Generate the mail content
    mail_msg = MIMEText(mail_template)
    mail_msg['From'] = conf['FROM_ADDRESS']
    mail_msg['Subject'] = "[WebPing] Alert: %s" % ', '.join([s for s in [fail_count and "%s failures" % fail_count or None, warning_count and "%s warnings" % warning_count or None] if s])
    mail_msg['To'] = ', '.join(conf['MAILING_LIST'])
    # Temporarily increase socket timeout to contact mail server
    socket.setdefaulttimeout(60)
    # Connect to server and send the mail alert
    mail_server = smtplib.SMTP(conf['MAIL_SERVER'])
    mail_server.sendmail(conf['FROM_ADDRESS'], conf['MAILING_LIST'], mail_msg.as_string())
    mail_server.close()
    # Set back to a more reasonable time out
    socket.setdefaulttimeout(conf['TIMEOUT'])

  # Place the HTML report beside the current script if the given destination is not absolute
  report_path = conf['DESTINATION_REPORT_FILE']
  if not os.path.isabs(report_path):
    report_path = os.path.abspath(os.path.join(script_folder, report_path))

  # Compute current script signature
  signature = "WebPing v%s" % __version__
 
  # Produce a nice HTML report ready to be published by Apache
  header = """<?xml version="1.0" encoding="utf-8"?>
  <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
      <meta http-equiv="Refresh" content="%(refresh_period)s"/>
      <meta name="generator" content="%(generator)s"/>
      <title>WebPing dashboard</title>
      <link rel="icon" type="image/png" href="img/%(global_status_icon)s"/>
      <link rel="stylesheet" type="text/css" href="css/style.css"/>
      <!--[if IE]><script src="js/excanvas.min.js" type="text/javascript"></script><![endif]-->
      <script src="js/jquery-1.3.2.min.js" type="text/javascript"></script>
      <script src="js/jquery.flot.min.js" type="text/javascript"></script>
      <script src="js/jquery.cuteTime.min.js" type="text/javascript"></script>
      <script type="text/javascript">
        $(document).ready(function () {
          // assign cuteTime controller to all 'timetamp' class objects
          $('.timestamp').cuteTime();
        });
      </script>
    </head>
    <body>
  """ % { 'refresh_period'    : conf['AUTO_REFRESH_DELAY'] * 60
        , 'generator'         : signature
        , 'global_status_icon': global_status_icon
        }

  body = """
      <h1>WebPing dashboard</h1>

      <div class="column c1">
        <p><strong>Summary</strong>:</p>
        <ul class="center-aligned">
          <li><span>%(total)s</span> URLs monitored</li>
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

  body += '\n'.join(["""<li><a href="mailto:%s">%s</a></li>""" %  tuple([email] * 2) for email in conf['MAILING_LIST']])

  body += """
        </ul>
      </div>

      <div class="column c3">
        <p><strong>WebPing configuration</strong>:</p>
        <ul>
          <li>Ping interval: likely set by a cron job</li>
          <li>Ping timeout: %(timeout)s seconds</li>
          <li>Ping response time threshold: %(response_threshold)s seconds</li>
          <li>SMTP server: <code>%(mail_server)s</code></li>
          <li>HTML report auto-refresh time: %(auto_refresh)s minutes</li>
          <li>HTML report path: <code>%(report_path)s</code></li>
          <li>Script location: <code>%(script_folder)s</code></li>
        </ul>
      </div>

      <table>
        <thead>
          <tr>
            <th>URL to check</th>
            <th>String to search</th>
            <th>Status</th>
            <th>Last check</th>
            <th>Response over time</th>
            <th>Last response time</th>
          </tr>
        </thead>
        <tbody>""" % { 'timeout'           : conf['TIMEOUT']
                     , 'mail_server'       : conf['MAIL_SERVER']
                     , 'report_path'       : report_path
                     , 'script_folder'     : script_folder
                     , 'auto_refresh'      : conf['AUTO_REFRESH_DELAY']
                     , 'response_threshold': conf['RESPONSE_TIME_THRESHOLD']
                     }

  # Compute all response time graph
  updated_result_list = []
  for site in result_list:
    site_url = site['url']
    site_id = md5.new(site_url).hexdigest()
    data_series = []
    for data_point in db.execute("SELECT check_time, response_time FROM %s WHERE url = '%s' ORDER BY check_time" % (TABLE_NAME, site_url)):
      response_time = data_point[1]
      if not response_time:
        continue
      (dt, ms) = data_point[0].split('.')
      check_time = datetime.datetime(*(time.strptime(dt, "%Y-%m-%d %H:%M:%S")[0:6])) + datetime.timedelta(microseconds = int(ms))
      data_series.append([time.mktime(check_time.timetuple()) * -1000, response_time])
    site['response_time_graph'] = """<div id="%s" style="width:100px;height:50px;"></div>
    <script id="source">
      $(function () {
        var d = %r;
        $.plot($("#%s"), [d], { lines: {show: true, fill: true}, xaxis: {mode: "time", ticks: []},  yaxis: {min: 0} });
      });
    </script>
    """ % (site_id, data_series, site_id)
    updated_result_list.append(site)
  result_list = updated_result_list

  body += '\n'.join(["""
          <tr>
            <td><a href="%(url)s">%(url_msg)s</a></td>
            <td class="%(str_class)s">%(str_msg)s</td>
            <td class="state %(state)s">%(status_msg)s</td>
            <td class="time"><abbr class="timestamp" title="%(update_time)s">%(update_msg)s</abbr></td>
            <td class="graph">%(response_time_graph)s</td>
            <td class="duration %(response_time_class)s">%(response_time_msg)s</td>
          </tr>""" % i for i in result_list])

  body += """
        </tbody>
      </table>"""

  footer = """
      <div id="footer">
        <p>HTML report generated <abbr class="timestamp" title="%(update_time)s">%(update_time)s</abbr>, by <strong>%(generator)s</strong>.</p>
      </div>
    </body>
  </html>""" % { 'update_time': datetime.datetime.now(conf['TIMEZONE']).strftime(DATETIME_FORMAT)
               , 'generator'  : signature
               }

  # Write the HTML report on the filesystem
  html_report = open(report_path, 'w')
  html_report.write(header + body + footer)
  html_report.close()

  # Close the database
  db.close()


if __name__ == '__main__':
  try:
    opts, args = getopt.getopt( sys.argv[1:]
                              , 'c:'
                              , ["config="]
                              )
  except getopt.GetoptError:
    print "FATAL - Bad command line options"
    sys.exit(2)

  conf = DEFAULT_CONF
  for o, a in opts:
    if o in ('-c', '--config'):
      conf = a

  webping(conf)
  sys.exit(0)
