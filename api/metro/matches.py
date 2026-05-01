from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import urllib.error
import json

INERTIA_VERSION = '59e066c5e19a8b0089b5210db0092dbc'

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        date        = qs.get('date',       [''])[0]
        gender_id   = qs.get('genderId',   [''])[0]
        category_id = qs.get('categoryId', [''])[0]
        division    = qs.get('division',   [''])[0]

        if not date:
            from datetime import date as dt
            date = dt.today().isoformat()

        try:
            params = f'status=upcoming&date={date}'
            if gender_id:   params += f'&genderId={gender_id}'
            if category_id: params += f'&categoryId={category_id}'

            url = f'https://metrovoley.com.ar/matches?{params}'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'X-Inertia': 'true',
                'X-Inertia-Version': INERTIA_VERSION,
                'X-Requested-With': 'XMLHttpRequest',
            })

            try:
                res = urllib.request.urlopen(req, timeout=10)
                raw = res.read()
            except urllib.error.HTTPError as e:
                if e.code == 409:
                    raw = e.read()
                else:
                    raise

            data  = json.loads(raw)
            props = data.get('props', {})
            matches = props.get('matches', [])
            items   = matches if isinstance(matches, list) else matches.get('data', [])

            items = [m for m in items if m.get('categoryName','') not in ['Superiores']]

            if division:
                items = [m for m in items if m.get('divisionName','') == division]

            if category_id:
                filters = props.get('filters', {})
                cats = {str(c['id']): c['name'] for c in filters.get('categories', [])}
                cat_name = cats.get(str(category_id))
                if cat_name:
                    items = [m for m in items if m.get('categoryName','') == cat_name]

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'matches': items, 'total': len(items)}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e), 'matches': []}).encode())
