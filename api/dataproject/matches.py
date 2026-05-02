from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import re
from datetime import datetime, timedelta

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

def parse_match_block(block, division_name):
    """Parsea un bloque de partido individual y retorna un dict o None."""
    # ChampionshipMatchID desde el onclick
    mid_m = re.search(r'MatchStatistics\.aspx\?mID=(\d+)', block)
    if not mid_m:
        return None
    match_id = int(mid_m.group(1))

    # Scores
    home_sets = int(m.group(1)) if (m := re.search(r'HF_WonSetHome[^>]*value="(\d+)"', block)) else 0
    away_sets = int(m.group(1)) if (m := re.search(r'HF_WonSetGuest[^>]*value="(\d+)"', block)) else 0

    # Fecha y hora
    datetime_m = re.search(r'HF_MatchDatetime[^>]*value="([^"]+)"', block)
    raw_dt = datetime_m.group(1).strip() if datetime_m else ''
    scheduled_at = None
    time_str = None
    if raw_dt:
        dt_parts = raw_dt.replace(' ', '').split('-')
        if len(dt_parts) >= 2:
            date_part = dt_parts[0]
            time_part = dt_parts[1][:5]
            time_str = time_part
            try:
                d, mo, y = date_part.split('/')
                scheduled_at = f"{y}-{mo.zfill(2)}-{d.zfill(2)}T{time_part}:00"
            except:
                pass

    # Filtrar: solo partidos de hoy hasta hoy + 20 días
    if scheduled_at:
        try:
            match_date = datetime.fromisoformat(scheduled_at).date()
            today = datetime.now().date()
            if match_date < today or match_date > today + timedelta(days=20):
                return None
        except:
            pass

    # Status
    status_id = 1
    if home_sets > 0 or away_sets > 0:
        status_id = 2
    elif scheduled_at:
        try:
            if datetime.fromisoformat(scheduled_at) < datetime.now():
                status_id = 2
        except:
            pass

    # Nombres — Label2=local, Label4=visitante (sufijos del id dinámico)
    team_names = re.findall(r'TeamName[^>]*>\s*([^<]{3,60}?)\s*<', block)
    if len(team_names) < 2:
        label2 = re.search(r'id="[^"]*_Label2"[^>]*>\s*([^<]{3,60}?)\s*<', block)
        label4 = re.search(r'id="[^"]*_Label4"[^>]*>\s*([^<]{3,60}?)\s*<', block)
        if label2 and label4:
            team_names = [label2.group(1).strip(), label4.group(1).strip()]
    home = team_names[0].strip() if len(team_names) > 0 else '—'
    away = team_names[1].strip() if len(team_names) > 1 else '—'

    return {
        'id': match_id,
        'home': home,
        'away': away,
        'time': time_str,
        'scheduledAt': scheduled_at,
        'statusId': status_id,
        'homeTeamSets': home_sets,
        'awayTeamSets': away_sets,
        'categoryName': division_name,
    }

def parse_fixture(html, division_name):
    matches = []
    seen_ids = set()

    # Dividir por bloques de jornada (HF_LegID)
    leg_blocks = re.split(r'(?=<input[^>]*name="[^"]*HF_LegID[^"]*")', html)

    for leg_block in leg_blocks[1:]:
        # Dentro de cada jornada, dividir por partido individual (HF_MatchDatetime)
        match_blocks = re.split(r'(?=<input[^>]*name="[^"]*HF_MatchDatetime[^"]*")', leg_block)

        for mb in match_blocks[1:]:
            result = parse_match_block(mb, division_name)
            if result and result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                matches.append(result)

    # Ordenar por fecha
    matches.sort(key=lambda m: m['scheduledAt'] or '')
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
