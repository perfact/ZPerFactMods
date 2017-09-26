# -*- coding: utf-8 -*-
#
# Alter the fallback error message to match the one defined for Apache
#

from ZPublisher import HTTPResponse

HTTPResponse.HTTPResponse.__old_error_html = HTTPResponse.HTTPResponse._error_html

def _error_html(self, title, body):
    return ("""\
<!DOCTYPE HTML>
<html>
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
    <script type="text/javascript">
      window.setInterval('window.location.reload()', 10000);
    </script>
  </head>
  <body style="background-color: #eee; margin: 0px">
    <div style="background-color: #555; color: white; height: 40px;">&nbsp;</div>
    <div style="align: center; margin: 20px;">
      <h1 style="font-size: 24px">Dienst kurzzeitig nicht erreichbar.</h1>
      <p>Bitte warten.</p>
      <p>Die Seite wird automatisch geladen, sobald der Dienst wieder verfügbar ist.</p>
    </div>
  </body>
</html>
""")

HTTPResponse.HTTPResponse._error_html = _error_html
