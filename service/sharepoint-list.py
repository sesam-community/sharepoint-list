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
logger.setLevel(os.environ.get('LOG_LEVEL', logging.INFO))

# auth = HttpNtlmAuth(os.environ.get('username'), os.environ.get('password'))


class DataAccess:

    def __get_list(self, path, args):

        log_string = "Fetching data from list: %s" % path
        url = os.environ.get("base_url") + path  # + "/items"
        since = args.get("since")

        if since is not None:
            log_string += ", since: %s" % since
            url += "?$filter=Modified gt datetime'" + since + "'"

        logger.info(log_string)
        logger.debug("URL: %s", url)

        if "username" not in os.environ or "password" not in os.environ:
            logger.error("missing username/password")
            yield

        headers = {
            'Accept': 'application/json;odata=verbose',
            'Content-type': 'application/json;odata=verbose'
        }
        # OData v4 accepts different headers
        # headers = {
        #     'Accept': 'application/json;odata.metadata=minimal;odata.streaming=true;IEEE754Compatible=false',
        #     'Content-type': 'application/json;odata.metadata=minimal;odata.streaming=true;IEEE754Compatible=false'
        # }
        logger.debug(f"headers: {headers}")

        req = requests.get(
            url,
            auth=HttpNtlmAuth(os.environ.get('username'), os.environ.get('password')),
            headers=headers)

        logger.debug(f"req: {req}")

        data = req.json()
        logger.debug(f"data: {data}")

        entities = self.get_entities(data)
        logger.debug(f"entities: {entities}")

        next = self.get_next_page(data)
        logger.debug(f"next: {next}")

        while next is not None:

            for entity in entities:
                logger.debug(f"entity: {entity}")
                yield set_updated(entity, args)

            # Odata v2/v3 returns full next URL; OData v4 does not
            # next_url = os.environ.get("base_url") + "/" + next
            # logger.debug(f"next_url: {next_url}")
            req = requests.get(
                next,
                auth=HttpNtlmAuth(os.environ.get('username'), os.environ.get('password')),
                headers=headers)

            data = req.json()
            entities = self.get_entities(data)
            next = self.get_next_page(data)
            logger.debug(f"next: {next}")

        else:
            for entity in entities:
                logger.debug(f"entity: {entity}")
                yield set_updated(entity, args)

        if req.status_code != 200:
            logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
            raise AssertionError("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))

    def get_list(self, path, args):
        logger.debug(f"getting list: {path}")
        return self.__get_list(path, args)

    def get_entities(self, data):
        """Drill down to the data of interest."""

        entities = None

        if "d" in data:
            logger.debug(f"'d' found.")
            if "results" in data.get("d"):
                logger.debug(f"'d.results' found.")
                entities = data["d"].get("results")
            else:
                entities = data.get("d")
        elif "value" in data:
            logger.debug(f"'value' found.")
            entities = data.get("value")
        else:
            logger.debug(f"No entities found.")

        return entities

    def get_next_page(self, data):
        """Fetch next page (if any)."""

        next_page = None

        if "d" in data:
            logger.debug(f"'d' found (OData v2).")
            if "__next" in data["d"]:
                logger.debug(f"'d.__next' found")
                next_page = data["d"].get("__next")
        elif "value" in data:
            logger.debug(f"'value' found (OData v3 or v4).")
            if "odata.nextLink" in data:
                logger.debug(f"'odata.nextLink' found (Odata v3).")
                next_page = data.get("odata.nextLink")
            elif "@odata.nextLink" in data:
                logger.debug(f"'@odata.nextLink' found (Odata v4).")
                next_page = data.get("@odata.nextLink")
        else:
            logger.debug(f"No more pages.")

        return next_page


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
    app.run(threaded=True, debug=True, host='0.0.0.0', port=os.environ.get('port', 5000))
