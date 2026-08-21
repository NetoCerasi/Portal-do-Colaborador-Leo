from http.server import BaseHTTPRequestHandler
import json, os, urllib.parse

# Load embedded database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database.json')

def get_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'employees': [], 'stores': [], 'users': []}

class handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ['/api/data', '/api/data.py']:
            db = get_db()
            self._send_json(db)
        elif path in ['/api/users', '/api/users.py']:
            db = get_db()
            self._send_json(db.get('users', []))
        elif path in ['/api/events', '/api/events.py']:
            self._send_json({'status': 'connected'})
        else:
            self._send_json({'error': 'Not found'}, status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(length) if length > 0 else b'{}'
        try:
            payload = json.loads(post_body.decode('utf-8'))
        except:
            payload = {}

        if path in ['/api/login', '/api/login.py']:
            email = payload.get('email', '').strip().lower()
            senha = payload.get('senha', '').strip()
            db = get_db()
            users = db.get('users', [])
            
            # Fallback admin check
            if (email == 'admin@leomadeiras.com.br' and senha == 'admin') or (email == 'admin' and senha == 'admin'):
                user_res = {
                    'id': 'usr_admin',
                    'nome': 'Neto Cerasi (Admin)',
                    'email': 'admin@leomadeiras.com.br',
                    'role': 'ADMIN',
                    'stores': ['ALL']
                }
                return self._send_json({'success': True, 'user': user_res})

            for u in users:
                if u.get('email', '').strip().lower() == email and str(u.get('senha', '')).strip() == senha:
                    u_clean = {k: v for k, v in u.items() if k != 'senha'}
                    return self._send_json({'success': True, 'user': u_clean})

            return self._send_json({'success': False, 'message': 'E-mail ou senha incorretos.'}, status=401)

        elif path in ['/api/users', '/api/users.py']:
            self._send_json({'success': True, 'user': payload})

        elif path in ['/api/employees', '/api/employees.py']:
            self._send_json({'success': True, 'employee': payload})

        else:
            self._send_json({'error': 'Not found'}, status=404)
