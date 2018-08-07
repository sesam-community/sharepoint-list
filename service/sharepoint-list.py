from flask import Flask, request, Response
import logging
import os
import requests
from requests_ntlm import HttpNtlmAuth
import json
from dotdictify import Dotdictify


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


class DataAccess:

    def __get_list(self, path, args):

        since = args.get("since")
        if since is not None:
            logger.info("Fetching data from list: %s, since %s", path, since)
            url = os.environ.get("base_url") + "getByTitle('" + path + "')/items?$filter=Modified gt datetime'" + since + "'"
        else:
            logger.info("Fetching data from list: %s", path)
            url = os.environ.get("base_url") + "getByTitle('" + path + "')/items"
        if "username" not in os.environ or "password" not in os.environ:
            logger.error("missing username/password")
            yield

        req = requests.get(url, auth=HttpNtlmAuth(os.environ.get("username"),os.environ.get("password")),headers={'Accept' : 'application/json'})
        next = json.loads(req.text).get('odata.nextLink')

        while next is not None:
            for entity in Dotdictify(json.loads(req.text)).value:
                yield set_updated(entity, args)
            req = requests.get(next, auth=HttpNtlmAuth(os.environ.get("username"), os.environ.get("password")), headers={'Accept': 'application/json'})
            next =json.loads(req.text).get('odata.nextLink')

        else:
            for entity in Dotdictify(json.loads(req.text)).value:
                yield set_updated(entity, args)

        if req.status_code != 200:
            logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
            raise AssertionError("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))


    def get_list(self, path, args):
        print('getting list')
        return self.__get_list(path, args)


data_access_layer = DataAccess()

def set_updated(entity, args):
    since_path = args.get("since_path")

    if since_path is not None:
        b = Dotdictify(entity)
        entity["_updated"] = b.get(since_path)

    return entity


def stream_json(clean):
    first = True
    yield '['
    for i, row in enumerate(clean):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'


@app.route("/<path:path>", methods=["GET"])
def get(path):
    entities = data_access_layer.get_list(path, args=request.args)
    return Response(
        stream_json(entities),
        mimetype='application/json'
    )


if __name__ == '__main__':
    app.run(threaded=True, debug=True, host='0.0.0.0', port=os.environ.get('port',5000))