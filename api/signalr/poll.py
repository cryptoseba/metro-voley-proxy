from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json

HUB_DATA = '[{"name":"signalrlivehubfederations"}]'
BASE = 'https://dataprojectservicesignalradv.azurewebsites.net/signalr'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fmv-web.dataproject.com/',
    'Origin': 'https://fmv-web.dataproject.com',
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        token = qs.get('token', [''])[0]
        msg_id = qs.get('messageId', [''])[0]

        try:
            poll_url = f'{BASE}/poll?transport=longPolling&clientProtocol=2.1&connectionToken={urllib.parse.quote(token)}&connectionData={urllib.parse.quote(HUB_DATA)}&messageId={urllib.parse.quote(msg_id)}'
            poll_req = urllib.request.Request(poll_url, headers=HEADERS)
            poll_resp = urllib.request.urlopen(poll_req, timeout=3)
            poll_data = json.loads(poll_resp.read())

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(poll_data).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
