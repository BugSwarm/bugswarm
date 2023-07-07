#!/usr/bin/env python3

import requests
import urllib.parse
import pickle
from flask import Flask, request, Response


app = Flask(__name__)
PORT = 56765


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    file_url = urllib.parse.quote(path, safe='')

    request_headers = {
        k: v for k, v in dict(request.headers).items()
        if k.lower() not in {'host'}
    }

    if 'Accept' in request_headers:
        # Future improvement, we can check Accept and cached Content-Type ourselves
        file_url = urllib.parse.quote('{}_{}'.format(path, request_headers['Accept']), safe='')

    try:
        with open('cache/{}'.format(file_url), 'rb') as cache, open('cache/{}.headers'
                                                                    .format(file_url), 'rb') as header:
            print('{}: Cache hit'.format(path))
            return Response(cache.read(), headers=pickle.load(header))
    except FileNotFoundError:
        print('{}: Cache miss'.format(path))
    except Exception as e:
        print('Unknown error when getting cache file: {}'.format(repr(e)))

    pythonhosted = False
    if request.url.startswith('http://localhost:{}/pythonhosted'.format(PORT)):
        pythonhosted = True
        url = request.url.replace(
            'http://localhost:{}/pythonhosted'.format(PORT),
            'https://files.pythonhosted.org'
        )
    else:
        url = request.url.replace(
            'http://localhost:{}'.format(PORT),
            'https://pypi.org'
        )

    try:
        response = requests.request(
            method=request.method,
            url=url,
            data=request.get_data(),
            headers=request_headers,
            cookies=request.cookies,
            allow_redirects=True
        )
    except Exception as e:
        print('Error when downloading file: {}'.format(repr(e)))
        return '', 404

    response_headers = {
        k: v for k, v in response.headers.items()
        if k.lower() not in {'content-encoding', 'content-length', 'connection', 'date'}
    }

    if not pythonhosted:
        if 'text' in response.headers['Content-Type'] or 'json' in response.headers['Content-Type']:
            content = response.text.replace(
                'https://files.pythonhosted.org',
                'http://localhost:{}/pythonhosted'.format(PORT)
            ).encode()
        else:
            content = response.content
    else:
        content = response.content

    with open('cache/{}'.format(file_url), 'wb') as cache, open('cache/{}.headers'.format(file_url), 'wb') as headers:
        pickle.dump(response_headers, headers)
        cache.write(content)
        print('{}: Saved to cache'.format(path))

    response = Response(content, headers=response_headers)
    return response


if __name__ == '__main__':
    app.run(port=PORT)
