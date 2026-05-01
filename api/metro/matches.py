from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        date       = qs.get('date',       [''])[0]
        gender_id  = qs.get('genderId',   [''])[0]
        category_id= qs.get('categoryId', [''])[0]
        division   = qs.get('division',   [''])[0]

        if not date:
            from datetime import date as dt
            date = dt.today().isoformat()

        try:
            # Use Inertia.js API
            params = f'status=upcoming&date={date}'
            if gender_id:   params += f'&genderId={gender_id}'
            if category_id: params += f'&categoryId={category_id}'

            url = f'https://metrovoley.com.ar/matches?{params}'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json',
                'X-Inertia': 'true',
            })
            res  = urllib.request.urlopen(req, timeout=10)
            data = json.loads(res.read())
            props   = data.get('props', {})
            matches = props.get('matches', {})
            items   = matches.get('data', []) if isinstance(matches, dict) else matches

            # Filter by division if specified
            if division:
                items = [m for m in items if m.get('divisionName','') == division]

            # Filter out Superiores category
            items = [m for m in items if m.get('categoryName','') not in ['Superiores']]

            result = json.dumps({'matches': items, 'total': len(items)})
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
            self.wfile.write(json.dumps({'error': str(e), 'matches': []}).encode())
