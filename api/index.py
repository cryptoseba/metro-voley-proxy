from http.server import BaseHTTPRequestHandler
import urllib.request
import json
import re
import time

# Cache: { match_id: { 'data': bytes, 'ts': float } }
_cache = {}
CACHE_TTL = 2  # segundos

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        match = re.search(r'/api/matches/(\w+)/updates', self.path)
        if match:
            match_id = match.group(1)
            now = time.time()

            # Devolver caché si es reciente
            cached = _cache.get(match_id)
            if cached and (now - cached['ts']) < CACHE_TTL:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('X-Cache', 'HIT')
                self.end_headers()
                self.wfile.write(cached['data'])
                return

            url = f'https://metrovoley.com.ar/api/matches/{match_id}/updates'
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                res = urllib.request.urlopen(req, timeout=10)
                data = res.read()

                # Guardar en caché
                _cache[match_id] = {'data': data, 'ts': now}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('X-Cache', 'MISS')
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'metro-voley-proxy'}).encode())
