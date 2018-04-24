from flask import Flask, request, Response
import logging
import os
from shareplum import Site
from requests_ntlm import HttpNtlmAuth
import json

app = Flask(__name__)
logger = None
format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger('sharepoint-list-service')

# Log to stdout
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(format_string))
logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)

auth = HttpNtlmAuth(os.environ.get('username'), os.environ.get('password'))


@app.route("/<path:path>", methods=["GET"])
def get(path):
    site = Site(os.environ.get('sharepoint_site'), auth=auth)
    sp_list = site.List(request.args['list'])
    data = sp_list.GetListItems(request.args['listItem'])
    return Response(
        json.dumps(data, default=str),
        mimetype='application/json'
    )


if __name__ == '__main__':
    app.run(threaded=True, debug=True, host='0.0.0.0', port=os.environ.get('port',5000))