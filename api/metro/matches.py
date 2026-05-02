from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime

# Mapa de divisiones disponibles
DIVISIONS = {
    'dh_cab': {'id': 55, 'name': 'División de Honor CAB'},
    'p1_cab': {'id': 53, 'name': 'Primera División CAB'},
    'p2_cab': {'id': 54, 'name': 'Segunda División CAB'},
    'dh_dam': {'id': 56, 'name': 'División de Honor DAM'},
    'p1_dam': {'id': 57, 'name': 'Primera División DAM'},
    'p2_dam': {'id': 58, 'name': 'Segunda División DAM'},
}

def fetch_fixture(competition_id):
    url = f'https://fmv-web.dataproject.com/CompetitionMatches.aspx?ID={competition_id}'
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'es-AR,es;q=0.9',
        }
    )
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    return html

def parse_fixture(html, division_name):
    matches = []

    # Extraer bloques de partido: cada uno tiene HF_LegID
    # Dividimos el HTML por bloques usando el patrón del LegID hidden field
    blocks = re.split(r'(?=<input[^>]*name="[^"]*HF_LegID[^"]*")', html)

    for block in blocks[1:]:  # skip first empty
        # LegID (ID del partido)
        leg_id_m = re.search(r'HF_LegID[^>]*value="(\d+)"', block)
        if not leg_id_m:
            continue
        match_id = int(leg_id_m.group(1))

        # Scores
        home_sets_m = re.search(r'HF_WonSetHome[^>]*value="(\d+)"', block)
        away_sets_m = re.search(r'HF_WonSetGuest[^>]*value="(\d+)"', block)
        home_sets = int(home_sets_m.group(1)) if home_sets_m else 0
        away_sets = int(away_sets_m.group(1)) if away_sets_m else 0

        # Fecha y hora: "24/4/2026 - 19:00"
        datetime_m = re.search(r'HF_MatchDatetime[^>]*value="([^"]+)"', block)
        raw_dt = datetime_m.group(1).strip() if datetime_m else ''
        scheduled_at = None
        time_str = None
        if raw_dt:
            # Parsear "24/4/2026 - 19:00" o "24/4/2026 - 19:00:00"
            dt_parts = raw_dt.replace(' ', '').split('-')
            if len(dt_parts) >= 2:
                date_part = dt_parts[0]  # "24/4/2026"
                time_part = dt_parts[1][:5]  # "19:00"
                time_str = time_part
                try:
                    d, m, y = date_part.split('/')
                    scheduled_at = f"{y}-{m.zfill(2)}-{d.zfill(2)}T{time_part}:00"
                except:
                    pass

        # Determinar status basado en si tiene score o fecha pasada
        status_id = 1  # próximo por default
        if home_sets > 0 or away_sets > 0:
            status_id = 2  # terminado
        elif scheduled_at:
            try:
                match_time = datetime.fromisoformat(scheduled_at)
                if match_time < datetime.now():
                    status_id = 2  # terminado
            except:
                pass

        # Filtrar partidos anteriores a hoy
        if scheduled_at:
            try:
                match_date = datetime.fromisoformat(scheduled_at).date()
                if match_date < datetime.now().date():
                    continue
            except:
                pass

        # Nombres de equipos — buscar spans con clase TeamName
        team_names = re.findall(r'TeamName[^>]*>([^<]{3,60})<', block)
        home = team_names[0].strip() if len(team_names) > 0 else '—'
        away = team_names[1].strip() if len(team_names) > 1 else '—'

        matches.append({
            'id': match_id,
            'home': home,
            'away': away,
            'time': time_str,
            'scheduledAt': scheduled_at,
            'statusId': status_id,
            'homeTeamSets': home_sets,
            'awayTeamSets': away_sets,
            'categoryName': division_name,
        })

    return matches

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parsear query params: ?division=dh_cab (default)
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            div_key = params.get('division', ['dh_cab'])[0]

            if div_key not in DIVISIONS:
                div_key = 'dh_cab'

            div = DIVISIONS[div_key]
            html = fetch_fixture(div['id'])
            matches = parse_fixture(html, div['name'])

            result = {
                'matches': matches,
                'total': len(matches),
                'division': div['name'],
                'divisions': {k: v['name'] for k, v in DIVISIONS.items()},
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e), 'matches': []}).encode())
