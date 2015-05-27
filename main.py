#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging

from google.appengine.api import memcache
from google.appengine.api import urlfetch
import webapp2
import urllib

CACHE_EXPIRATION = 60 * 30 # 1/2 hour


class MainHandler(webapp2.RequestHandler):

    def post(self):
        headers = self.request.headers
        if not ('origin' in headers) or headers['origin'] != 'blissflixx':
            self.response.set_status(403)
            return

        url = None
        form_fields = {}
        for v, k in self.request.POST.iteritems():
            if v == '__url__':
                url = k
            else:
                form_fields[v] = k.encode('utf-8')
        form_data = urllib.urlencode(form_fields)

        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        result = urlfetch.fetch(url=url,
                 payload=form_data, method=urlfetch.POST, deadline=60,
                 headers=headers)
        if result.status_code != 200:
            result.content = 'Cannot POST %s' % url
        self.generate_response(result.content, result.headers, result.status_code)

    def get(self):

        headers = self.request.headers
        if not ('origin' in headers) or headers['origin'] != 'blissflixx':
            self.response.set_status(403)
            return

        url = self.request.get('url')

        if url.startswith("https://yts.re"):
          url = "https://yts.to" + url[14:]
        elif url.startswith("https://thepiratebay.se"):
          url = "https://thepiratebay.am" + url[23:]

        callback = self.request.get('callback', None)

        content = memcache.get(url)
        headers = memcache.get('%s:headers' % url)
        status = memcache.get('%s:status' % url)
        if content and headers and status:
            logging.info('cache hit')
            self.generate_response(content, headers, status, callback)
        else:
            logging.info('cache miss')
            result = urlfetch.fetch(url, headers=self.request.headers, deadline=60)
            if result.status_code != 200:
                result.content = 'Cannot GET %s' % url

            self.generate_response(result.content, result.headers, result.status_code, callback)

            memcache.set(url, result.content, CACHE_EXPIRATION)
            memcache.set('%s:headers' % url, result.headers, CACHE_EXPIRATION)
            memcache.set('%s:status' % url, result.status_code, CACHE_EXPIRATION)


    def generate_response(self, content, headers, status, callback=None):
        if callback is not None:
            self.response.write(callback + '(' + content + ')')
        else:
            self.response.write(content)
        for key, value in headers.items():
            self.response.headers.add_header(key, value)
        self.response.headers.add_header('Access-Control-Allow-Origin', '*')
        self.response.set_status(status)


app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=False)
