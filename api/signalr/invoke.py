from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import time

HUB_DATA = '[{"name":"signalrlivehubfederations"}]'
BASE = 'https://dataprojectservicesignalradv.azurewebsites.net/signalr'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fmv-web.dataproject.com/',
    'Origin': 'https://fmv-web.dataproject.com',
}

# Cache para getLiveScoreData: { match_id: { 'result': dict, 'ts': float } }
_score_cache = {}
CACHE_TTL = 2  # segundos

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))

        token    = body.get('token', '')
        msg_id   = body.get('messageId', '')
        method   = body.get('method', 'getLiveScoreData_From_DV')
        args     = body.get('args', [])
        invoke_id = body.get('invokeId', 1)

        try:
            # Caché solo para getLiveScoreData_From_DV
            if method == 'getLiveScoreData_From_DV' and args:
                match_id = str(args[0])
                now = time.time()
                cached = _score_cache.get(match_id)
                if cached and (now - cached['ts']) < CACHE_TTL:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('X-Cache', 'HIT')
                    self.end_headers()
                    self.wfile.write(json.dumps({'result': cached['result'], 'error': None}).encode())
                    return

            token_enc = urllib.parse.quote(token)
            conn_data_enc = urllib.parse.quote(HUB_DATA)

            send_url = f'{BASE}/send?transport=longPolling&clientProtocol=2.1&connectionToken={token_enc}&connectionData={conn_data_enc}'
            payload_json = json.dumps({"H": "signalrlivehubfederations", "M": method, "A": args, "I": invoke_id})
            payload = ('data=' + urllib.parse.quote(payload_json)).encode()
            send_req = urllib.request.Request(send_url, data=payload, headers={
                **HEADERS,
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            send_resp = urllib.request.urlopen(send_req, timeout=10)
            send_data = json.loads(send_resp.read())
            result_data = send_data.get('R')

            # Guardar en caché
            if method == 'getLiveScoreData_From_DV' and args and result_data:
                _score_cache[str(args[0])] = {'result': result_data, 'ts': time.time()}

            result = json.dumps({'result': result_data, 'error': send_data.get('E')})

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('X-Cache', 'MISS')
            self.end_headers()
            self.wfile.write(result.encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

