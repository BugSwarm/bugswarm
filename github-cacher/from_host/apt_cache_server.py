import json
import urllib.parse
from pathlib import Path

import requests
from flask import Flask, request

PORT = 56766
CACHE_PATH = Path.cwd() / 'apt-cache'
LOG_PATH = Path.cwd() / 'apt-cache.log'
APP_NAME = 'bugswarm::apt-cache-server'

app = Flask(APP_NAME)
app.logger.setLevel('INFO')


def log_response_data(content, status, headers):
    app.logger.info('  status code: %s', status)
    app.logger.info('  length: %s', len(content))
    if headers:
        app.logger.info('  headers: %s', headers)


@app.route('/', defaults={'_': ''})
@app.route('/<path:_>')
def proxy(_):
    hostname = request.host.split(':')[0]
    if hostname in ['localhost', '127.0.0.1']:
        return 'Error: Host header must not be localhost!\n', 403

    file_url = urllib.parse.quote(request.base_url, safe='')
    cache_dir = CACHE_PATH / file_url
    response_path = cache_dir / 'response'
    metadata_path = cache_dir / 'metadata.json'

    app.logger.info('New request: %s', request.base_url)
    app.logger.info('  cache path: %s', cache_dir)
    app.logger.info('  headers: %s', dict(request.headers))

    if req_data := request.get_data():
        app.logger.info('  payload (%s bytes): %r', len(req_data), req_data)

    # Look in cache first
    if cache_dir.is_dir():
        app.logger.info('Cache hit: %s', request.base_url)

        try:
            # Read the cached response and metadata
            with open(response_path, 'rb') as f:
                response_content = f.read()
            with open(metadata_path) as f:
                metadata = json.load(f)
                response_status = metadata['status']
                response_headers = metadata['headers']
        except Exception:
            app.logger.exception('Error reading cache for "%s", treating as a miss', request.base_url)
        else:
            log_response_data(response_content, response_status, response_headers)
            return response_content, response_status, response_headers.items()

    app.logger.info('Cache miss: %s', request.base_url)
    # Cache miss; make a request and store it in the cache
    response = requests.request(
        method=request.method,
        url=request.url,
        data=request.get_data(),
        headers=request.headers,
        cookies=request.cookies,
        allow_redirects=True,
    )

    # Probably unnecessary since Flask overrides the Date header anyway
    if 'Date' in response.headers:
        del response.headers['Date']

    log_response_data(response.content, response.status_code, response.headers)

    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(response_path, 'wb') as f:
        f.write(response.content)
    with open(metadata_path, 'w') as f:
        json.dump({'status': response.status_code, 'headers': dict(response.headers)}, f)

    return response.content, response.status_code, response.headers.items()


if __name__ == '__main__':
    app.run(port=PORT)
