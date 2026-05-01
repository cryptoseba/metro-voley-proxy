from http.server import BaseHTTPRequestHandler
import urllib.request
import json
import re
import http.cookiejar

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            cookiejar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))
            req = urllib.request.Request(
                'https://fmv-web.dataproject.com/MainLiveScore.aspx',
                headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}
            )
            html = opener.open(req, timeout=10).read().decode('utf-8', errors='ignore')

            ids = re.findall(r'RLV_MatchList_Label1_(\d+)', html)
            ids = list(dict.fromkeys(ids))

            matches = []
            for mid in ids:
                home_m = re.search(rf'Label1_{mid}"[^>]*>([^<]+)<', html)
                away_m = re.search(rf'Label2_{mid}"[^>]*>([^<]+)<', html)
                time_m = re.search(rf'MatchTime_{mid}"[^>]*>([^<]+)<', html)
                score_m = re.search(rf'MatchResult_{mid}.*?(\d+)\s*[-–]\s*(\d+)', html, re.DOTALL)

                home = home_m.group(1).strip() if home_m else '—'
                away = away_m.group(1).strip() if away_m else '—'
                time = time_m.group(1).strip() if time_m else None
                score = f"{score_m.group(1)}-{score_m.group(2)}" if score_m else None

                matches.append({
                    'id': int(mid),
                    'home': home,
                    'away': away,
                    'time': time,
                    'score': score,
                    'statusId': 3,
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
