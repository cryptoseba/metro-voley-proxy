from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import http.cookiejar

HUB_DATA = '[{"name":"signalrlivehubfederations"}]'
BASE = 'https://dataprojectservicesignalradv.azurewebsites.net/signalr'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://fmv-web.dataproject.com/',
    'Origin': 'https://fmv-web.dataproject.com',
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse matchId from query string
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        match_id = qs.get('matchId', [''])[0]

        try:
            cookiejar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))

            # Get cookies from DataProject
            opener.open(f'https://fmv-web.dataproject.com/LiveScore_adv.aspx?ID={match_id}')

            # Negotiate
            neg_url = f'{BASE}/negotiate?clientProtocol=2.1&connectionData={urllib.parse.quote(HUB_DATA)}'
            neg_req = urllib.request.Request(neg_url, headers=HEADERS)
            neg_data = json.loads(opener.open(neg_req).read())

            # Connect
            token = neg_data['ConnectionToken']
            connect_url = f'{BASE}/connect?transport=longPolling&clientProtocol=2.1&connectionToken={urllib.parse.quote(token)}&connectionData={urllib.parse.quote(HUB_DATA)}'
            connect_resp = opener.open(urllib.request.Request(connect_url, headers=HEADERS), timeout=10)
            connect_data = json.loads(connect_resp.read())
            msg_id = connect_data.get('C', '')

            result = json.dumps({
                'token': token,
                'messageId': msg_id
            })

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(result.encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
