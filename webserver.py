import logging
import time
import cherrypy
from flask import Flask
from paste.translogger import TransLogger
from flasgger import Swagger

app = Flask(__name__)


app.config['SWAGGER'] = {
    "swagger_version": "2.0",
    "specs": [
        {
            "version": "1.0.0",
            "endpoint": 'v1_spec',
            "route": '/spec',
            "description": "API"
        }
    ]
}

swagger = Swagger(app)

handler_file =logging.FileHandler('access.log')
handler_file.setFormatter(logging.Formatter('%(message)s'))
logging.basicConfig(handlers=[handler_file], level=logging.INFO)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return "Naip API ok"


class FotsTransLogger(TransLogger):
    def write_log(self, environ, method, req_uri, start, status, bytes):
        """override the write_log function to remove the time offset so
        that the output aligns nicely with CherryPy's web server logging

        i.e.
        [08/Jan/2013:23:50:03] ENGINE Serving on 0.0.0.0:5000
        [08/Jan/2013:23:50:03] ENGINE Bus STARTED
        [08/Jan/2013:23:50:45 +1100] REQUEST GET 200 / (192.168.172.1) 830

        becomes

        [08/Jan/2013:23:50:03] ENGINE Serving on 0.0.0.0:5000
        [08/Jan/2013:23:50:03] ENGINE Bus STARTED
        [08/Jan/2013:23:50:45] REQUEST GET 200 / (192.168.172.1) 830
        """

        if bytes is None:
            bytes = '-'
        remote_addr = '-'
        if environ.get('HTTP_X_FORWARDED_FOR'):
            remote_addr = environ['HTTP_X_FORWARDED_FOR']
        elif environ.get('REMOTE_ADDR'):
            remote_addr = environ['REMOTE_ADDR']
        d = {
            'REMOTE_ADDR': remote_addr,
            'REMOTE_USER': environ.get('REMOTE_USER') or '-',
            'REQUEST_METHOD': method,
            'REQUEST_URI': req_uri,
            'HTTP_VERSION': environ.get('SERVER_PROTOCOL'),
            'time': time.strftime('%d/%b/%Y:%H:%M:%S', start),
            'status': status.split(None, 1)[0],
            'bytes': bytes,
            'HTTP_REFERER': environ.get('HTTP_REFERER', '-'),
            'HTTP_USER_AGENT': environ.get('HTTP_USER_AGENT', '-'),
        }
        message = self.format % d
        self.logger.log(self.logging_level, message)

if __name__ == "__main__":
    # Enable WSGI access logging via Paste

    log_format = (
        '[%(time)s] REQUEST %(REQUEST_METHOD)s %(status)s %(REQUEST_URI)s '
        '(%(REMOTE_ADDR)s) %(bytes)s'
    )
    app_logged = FotsTransLogger(app, format=log_format)

    logger = logging.getLogger('wsgi')
    logger.addHandler(handler_file)

    # Mount the WSGI callable object (app) on the root directory
    cherrypy.tree.graft(app_logged, '/app')


    # Set the configuration of the web server
    cherrypy.config.update({
        'engine.autoreload_on': True,
        'log.screen': True,
        'server.socket_port': 5000,
        'server.socket_host': '0.0.0.0',
        'server.thread_pool': 100
    })

    # Start the CherryPy WSGI web server
    cherrypy.engine.start()
    cherrypy.engine.block()
