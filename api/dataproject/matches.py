from http.server import BaseHTTPRequestHandler
import urllib.request
import json
import http.cookiejar

CHAMPIONSHIP_ID = 73  # FMV División de Honor

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            cookiejar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))

            # 1. Obtener cookies necesarias visitando la página principal
            req_cookies = urllib.request.Request(
                f'https://fmv-web.dataproject.com/CompetitionLive.aspx?ID={CHAMPIONSHIP_ID}',
                headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}
            )
            opener.open(req_cookies, timeout=10)

            # 2. Llamar a la API JSON de DataProject
            payload = json.dumps({
                'championshipId': CHAMPIONSHIP_ID,
                'language': 'es'
            }).encode()

            req_api = urllib.request.Request(
                'https://fmv-web.dataproject.com/api/LiveScore/getLiveScoreListData_From_ES',
                data=payload,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f'https://fmv-web.dataproject.com/CompetitionLive.aspx?ID={CHAMPIONSHIP_ID}'
                }
            )
            resp = opener.open(req_api, timeout=10)
            raw = json.loads(resp.read().decode('utf-8'))

            # raw puede ser una lista directa o tener una clave d / result
            items = raw if isinstance(raw, list) else raw.get('d', raw.get('result', raw.get('matches', [])))

            matches = []
            for m in items:
                mid = m.get('ChampionshipMatchID') or m.get('id')
                if not mid:
                    continue

                home = m.get('HomeEmpty') or m.get('home') or '—'
                away = m.get('GuestEmpty') or m.get('away') or '—'

                # Hora desde MatchDateTime  "2026-05-01T19:00:00"
                dt = m.get('MatchDateTime') or m.get('matchDateTime') or ''
                time_str = dt[11:16] if len(dt) >= 16 else None   # "19:00"
                date_str = dt[:10] if len(dt) >= 10 else None      # "2026-05-01"

                # Status: 0=no empezado, 1=en juego, 2=terminado
                status_raw = m.get('Status', m.get('status', 0))
                status_id  = 3 if status_raw == 1 else (2 if status_raw == 2 else 1)
                # (normalizamos a convención del panel: 3=en juego, 2=terminado, 1=próximo)

                # Score de sets
                home_sets = m.get('WonSetHome', 0)
                away_sets = m.get('WonSetGuest', 0)

                matches.append({
                    'id':          mid,
                    'home':        home,
                    'away':        away,
                    'time':        time_str,
                    'scheduledAt': f"{date_str}T{time_str}:00" if date_str and time_str else None,
                    'statusId':    status_id,
                    'homeTeamSets': home_sets,
                    'awayTeamSets': away_sets,
                    'categoryName': 'División de Honor',
                })

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'matches': matches, 'total': len(matches)}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e), 'matches': []}).encode())
