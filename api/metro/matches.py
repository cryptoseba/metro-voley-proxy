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
            params = f'date={date}'
            if gender_id:   params += f'&genderId={gender_id}'
            if category_id: params += f'&category={category_id}'
            if division:    params += f'&division={division}'

            # Paginar hasta traer todos los partidos
            items = []
            page = 1
            while True:
                paged_params = params + f'&page={page}'
                url = f'https://metrovoley.com.ar/matches?{paged_params}'
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

                if isinstance(matches, list):
                    # MetroVoley devuelve lista directa — igual intentar siguiente página
                    items.extend(matches)
                    if len(matches) == 0:
                        break
                    # Si trajo menos de 15, probablemente es la última página
                    if len(matches) < 15:
                        break
                    page += 1
                    if page > 50:
                        break
                else:
                    page_data = matches.get('data', [])
                    items.extend(page_data)
                    # Verificar si hay más páginas
                    meta = matches.get('meta', matches.get('links', {}))
                    current = meta.get('current_page', page)
                    last = meta.get('last_page', meta.get('total_pages', 1))
                    if current >= last or len(page_data) == 0:
                        break
                    page += 1
                    if page > 50:  # safety cap
                        break

            items = [m for m in items if m.get('categoryName','') not in ['Superiores']]

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
