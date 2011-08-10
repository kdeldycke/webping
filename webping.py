#!/usr/local/bin/python2.4
# -*- coding: utf-8 -*-

# Current WebPing version
__version__ = '0.4.dev'


import csv
import sys
import gzip
import time
import yaml
import getopt
import socket
import random
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
  # Calculate WebPinf own's computation time
  webping_start_time = datetime.datetime.now()

  # Where we are now
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
                                  , status_msg    TEXT
                                  , check_time    TEXT
                                  , response_time REAL
                                  )""" % TABLE_NAME)

  # Transform any string to a safe ID
  getSafeId = lambda s: ''.join([s[i].isalnum() and s[i] or ((i > 0 and i < len(s)-1 and s[i-1].isalnum()) and '-' or '') for i in range(len(s))]).lower()

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
      result['str_class'] = 'unknown'
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
      req.add_header('Referer'        , "http://github.com/kdeldycke/webping")
      req.add_header('Accept-encoding', 'gzip')
      start_time = datetime.datetime.now()
      fetcher = urllib2.urlopen(req)
      response_time = datetime.datetime.now() - start_time
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
  db.executemany("""INSERT INTO %s (url     , string  , status    , status_msg     , check_time      , response_time     )
                            VALUES (?       , ?       , ?         , ?              , ?               , ?                 )""" % TABLE_NAME
                ,                 [(d['url'], d['str'], d['state'], d['status_msg'], d['update_time'], d['response_time']) for d in result_list]
                )

  # End of the data collecting phase, commit our changes in the database
  db.commit()

  # Dump raw data in CSV files
  export_folder = os.path.abspath(os.path.join(script_folder, conf['EXPORT_FOLDER']))
  if not os.path.exists(export_folder):
    os.makedirs(export_folder)

  updated_result_list = []
  for site in result_list:
    site_url = site['url']
    site_id = getSafeId(site_url)
    site['csv_path'] = '/'.join([conf['EXPORT_FOLDER'], "%s.csv" % site_id])
    csv_file_path = os.path.join(export_folder, "%s.csv" % site_id)
    # If the file already exist, just append our latest datas. Else, generate a big database dump.
    if os.path.exists(csv_file_path):
      csv_file = open(csv_file_path, 'a')
      writer = csv.writer(csv_file)
      writer.writerow([site_url, site['str'], site['state'], site['status_msg'], site['update_time'], site['response_time']])
      csv_file.close()
    else:
      csv_data = [["url", "string", "status", "status_msg", "check_time", "response_time"]]
      column_names = ','.join(csv_data[0])
      for r in db.execute("SELECT %s FROM %s WHERE url = '%s' ORDER BY check_time ASC" % (column_names, TABLE_NAME, site_url)):
        csv_data.append(r)
      csv_file = open(csv_file_path, 'w')
      writer = csv.writer(csv_file)
      writer.writerows(csv_data)
      csv_file.close()
    updated_result_list.append(site)
  result_list = updated_result_list

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

  # Here we send mail alerts if something is wrong as soon as we're done with data gathering.
  mailing_list = conf.get('MAILING_LIST', [])
  # Desactivate mail alerts if no one is in the mailing list
  if mailing_list and (fail_count > 0 or warning_count > 0):
    # Sort mail for beautiful display
    mailing_list.sort()
    conf['MAILING_LIST'] = mailing_list
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
    mail_msg['To'] = ', '.join(mailing_list)
    # Temporarily increase socket timeout to contact mail server
    socket.setdefaulttimeout(60)
    # Connect to server and send the mail alert
    mail_server = smtplib.SMTP(conf['MAIL_SERVER'])
    mail_server.sendmail(conf['FROM_ADDRESS'], mailing_list, mail_msg.as_string())
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
      <script src="js/jquery.flot.threshold.min.js" type="text/javascript"></script>
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

  body += '\n'.join(["""<li><a href="mailto:%s">%s</a></li>""" %  tuple([email] * 2) for email in mailing_list]) or "<li>No one, so mail alerts are not activated.</li>"

  body += """
        </ul>
      </div>

      <div class="column c3">
        <p><strong>WebPing configuration</strong>:</p>
        <ul>
          <li>Ping interval: likely set by a cron job</li>
          <li>Ping timeout: %(timeout)s seconds</li>
          <li>Graph history: %(graph_history)s days</li>
          <li>Ping response time threshold: %(response_threshold)s seconds</li>
          <li>SMTP server: <code>%(mail_server)s</code></li>
          <li>HTML report auto-refresh time: %(auto_refresh)s minutes</li>
          <li>HTML report path: <code>%(report_path)s</code></li>
          <li>Script location: <code>%(script_folder)s</code></li>
          <li>Export folder: <code>%(export_folder)s</code></li>
        </ul>
      </div>

      <table>
        <thead>
          <tr>
            <th>URL to check</th>
            <th>String to search</th>
            <th>Status</th>
            <th>Last update</th>
            <th>Response time over the last %(graph_history)s days</th>
            <th>Last response time</th>
            <th>Last issue</th>
            <th>Raw data</th>
          </tr>
        </thead>
        <tbody>""" % { 'timeout'           : conf['TIMEOUT']
                     , 'mail_server'       : conf['MAIL_SERVER']
                     , 'report_path'       : report_path
                     , 'script_folder'     : script_folder
                     , 'auto_refresh'      : conf['AUTO_REFRESH_DELAY']
                     , 'graph_history'     : conf['GRAPH_HISTORY']
                     , 'response_threshold': conf['RESPONSE_TIME_THRESHOLD']
                     , 'export_folder'     : export_folder
                     }

  # Compute all response time graph
  updated_result_list = []
  graph_max_time = datetime.datetime.now()
  graph_min_time = graph_max_time + datetime.timedelta(-conf['GRAPH_HISTORY'])
  for site in result_list:
    site['response_time_graph'] = "no data"
    site_url = site['url']
    site_uid = getUID()
    data_series = []
    for (check_time, response_time) in db.execute("SELECT check_time, response_time FROM %s WHERE url = '%s' ORDER BY check_time DESC" % (TABLE_NAME, site_url)):
      if not response_time:
        if len(data_series) > 0 and data_series[-1] != 'null':
          data_series.append('null')
      else:
        data_series.append([getJSEpochFromDateTime(getDateTimeFromString(check_time)), response_time])
        if getDateTimeFromString(check_time) < graph_min_time:
          break
    data_series = data_series[::-1]
    if len(data_series) > 0:
      render_point = lambda d: d == 'null' and d or '%r' % d
      data_series_str = ", ".join([render_point(d) for d in data_series])
      site['response_time_graph'] = """<div id="%s" style="width:100px;height:50px;"></div>
      <script type="text/javascript">
        $(function () {
          var d = [%s];
          $.plot($("#%s"), [{
              data: d,
              color: "rgb(225, 55, 55)",
              threshold: {below: %s, color: "rgb(10, 176, 6)"},
              lines: {steps: false , fill: true}
          }], {
              xaxis: {mode: "time", min: %i, max: %i, ticks: []},
              yaxis: {min: 0, tickDecimals: 2, labelWidth: 20},
              grid: {borderWidth: 0, labelMargin: 2}
          });
        });
      </script>
      """ % (site_uid, data_series_str, site_uid, conf['RESPONSE_TIME_THRESHOLD'], getJSEpochFromDateTime(graph_min_time), getJSEpochFromDateTime(graph_max_time))
    updated_result_list.append(site)
  result_list = updated_result_list

  # Get the list of last issues
  updated_result_list = []
  for site in result_list:
    site_url = site['url']
    last_issue_msg = "no recorded incident"
    last_issue_class = "unknown"
    for r in db.execute("SELECT check_time, status_msg FROM %s WHERE url = '%s' AND response_time IS NULL ORDER BY check_time DESC LIMIT 1" % (TABLE_NAME, site_url)):
      last_issue = getDateTimeFromString(r[0])
      last_issue_msg = """<abbr class="timestamp" title="%s">%s</abbr> (%s)""" % (last_issue.isoformat(' '), last_issue.strftime(DATETIME_FORMAT), r[1])
      last_issue_class = ""
      break
    site['last_issue_msg'] = last_issue_msg
    site['last_issue_class'] = last_issue_class
    updated_result_list.append(site)
  result_list = updated_result_list

  body += '\n'.join(["""
          <tr>
            <td><a href="%(url)s">%(url_msg)s</a></td>
            <td class="%(str_class)s">%(str_msg)s</td>
            <td class="state %(state)s">%(status_msg)s</td>
            <td class="time"><abbr class="timestamp" title="%(update_time)s">%(update_msg)s</abbr></td>
            <td class="graph %(response_time_class)s">%(response_time_graph)s</td>
            <td class="duration %(response_time_class)s">%(response_time_msg)s</td>
            <td class="time %(last_issue_class)s">%(last_issue_msg)s</td>
            <td class="download"><a href="%(csv_path)s" title="Download CSV export of raw data"><img src="img/csv.png"/></a></td>
          </tr>""" % i for i in result_list])

  body += """
        </tbody>
      </table>"""

  webping_time = datetime.datetime.now() - webping_start_time

  footer = """
      <div id="footer">
        <p>HTML report generated <abbr class="timestamp" title="%(update_time)s">%(update_time)s</abbr>, in %(render_time)s, by <a href="http://github.com/kdeldycke/webping/tree/%(repository_tag)s" target="_blank">%(generator)s</a>.</p>
      </div>
    </body>
  </html>""" % { 'update_time'   : datetime.datetime.now(conf['TIMEZONE']).strftime(DATETIME_FORMAT)
               , 'render_time'   : "%.3f s." % ((webping_time.days * 24 * 60 * 60) + webping_time.seconds + (webping_time.microseconds / 1000000.0))
               , 'repository_tag': __version__.endswith('dev') and 'master' or __version__
               , 'generator'     : signature
               }

  # Write the HTML report on the filesystem
  html_report = open(report_path, 'w')
  html_report.write(header + body + footer)
  html_report.close()

  # Close the database
  db.close()


def getDateTimeFromString(s):
  """ Convert a date time string extracted from the database to a true DateTime Python object
  """
  (dt, ms) = s.split('.')
  return datetime.datetime(*(time.strptime(dt, "%Y-%m-%d %H:%M:%S")[0:6])) + datetime.timedelta(microseconds = int(ms))


def getJSEpochFromDateTime(dt):
  """ Convert a Python DateTime object to JavaScript's Epoch
  """
  return time.mktime(dt.timetuple()) * 1000


def getUID():
  """ Get a UID composed of 32 lower-case ASCII characters only.
  """
  UID_LENGHT = 32
  global already_generated
  already_generated = []
  new_uid = None
  while True:
    new_uid = ''.join([chr(random.randint(97, 122)) for i in range(UID_LENGHT)])
    if new_uid not in already_generated:
      already_generated.append(new_uid)
      break
  return new_uid


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
