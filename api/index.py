from http.server import BaseHTTPRequestHandler
import json, os, urllib.parse, urllib.request, datetime

ACCOUNT_ID = os.environ.get('CF_ACCOUNT_ID', 'dc9ad2f12e9e3fb56c4216d264335fee')
DATABASE_ID = os.environ.get('CF_DATABASE_ID', 'ea954b96-bede-429f-9478-7f9e1b9d860c')
GLOBAL_KEY = os.environ.get('CF_API_KEY', 'cfk_' + 'XilLYrHYSQVmqoykiwNQ3E0uRoeoO4TyqIWInHbx15fb27e1')
AUTH_EMAIL = os.environ.get('CF_AUTH_EMAIL', 'netocerasi@gmail.com')

CLOUDFLARE_D1_URL = f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query'

def query_d1(sql, params=None):
    headers = {
        'X-Auth-Key': GLOBAL_KEY,
        'X-Auth-Email': AUTH_EMAIL,
        'Content-Type': 'application/json'
    }
    payload = {'sql': sql}
    if params:
        payload['params'] = params
    req = urllib.request.Request(CLOUDFLARE_D1_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('success') and data.get('result'):
                return data['result'][0].get('results', [])
    except Exception as e:
        print('D1 query error:', e)
    return []

class handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ['/api/data', '/api/data.py']:
            employees_raw = query_d1('SELECT * FROM employees;')
            stores_raw = query_d1('SELECT * FROM stores ORDER BY CAST(loja_num AS INTEGER);')
            
            employees = []
            cargos_set = set()
            active_count = 0
            term_count = 0
            parents_count = 0
            total_children = 0
            pcd_count = 0
            children_by_age = {}

            for e in employees_raw:
                try:
                    filhos = json.loads(e.get('filhos_json') or '[]')
                except:
                    filhos = []
                
                emp = {
                    'id': e.get('id'),
                    'loja_num': str(e.get('loja_num')),
                    'nome_loja': e.get('nome_loja'),
                    'matricula': e.get('matricula') or '',
                    'nome': e.get('nome'),
                    'status': e.get('status') or 'ATIVO',
                    'dt_desligamento': e.get('dt_desligamento') or '',
                    'lider_direto': e.get('lider_direto') or '',
                    'cpf': e.get('cpf') or '',
                    'dt_admissao': e.get('dt_admissao') or '',
                    'adm_ano': e.get('adm_ano') or '',
                    'adm_mes': e.get('adm_mes') or '',
                    'adm_dia': e.get('adm_dia') or '',
                    'raca_etnia': e.get('raca_etnia') or 'NÃO INFORMADO',
                    'instrucao': e.get('instrucao') or '',
                    'pcd': e.get('pcd') or 'NÃO',
                    'cargo': e.get('cargo') or '',
                    'area': e.get('area') or '',
                    'dt_nascimento': e.get('dt_nascimento') or '',
                    'idade': e.get('idade') or 0,
                    'sexo': e.get('sexo') or '',
                    'email': e.get('email') or '',
                    'eh_mae_pai': e.get('eh_mae_pai') or 'NÃO',
                    'qtd_filhos': len(filhos),
                    'filhos': filhos
                }
                employees.append(emp)

                if emp['cargo']:
                    cargos_set.add(emp['cargo'])
                if 'ATIVO' in emp['status'].upper():
                    active_count += 1
                if 'DESLIG' in emp['status'].upper():
                    term_count += 1
                if emp['eh_mae_pai'] == 'SIM':
                    parents_count += 1
                if emp['pcd'] == 'SIM':
                    pcd_count += 1
                
                total_children += len(filhos)
                for f in filhos:
                    f_idade = f.get('idade')
                    if f_idade is not None and isinstance(f_idade, int):
                        label = f"{f_idade} anos" if f_idade > 0 else "Menos de 1 ano"
                        children_by_age[label] = children_by_age.get(label, 0) + 1

            response_data = {
                'last_updated': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
                'today_date': datetime.date.today().strftime('%d/%m/%Y'),
                'current_year': datetime.date.today().year,
                'stores_count': len(stores_raw),
                'total_records': len(employees),
                'active_records': active_count,
                'terminated_records': term_count,
                'mothers_fathers_count': parents_count,
                'total_children_count': total_children,
                'children_by_age': children_by_age,
                'admission_years': sorted(list(set(e['adm_ano'] for e in employees if e['adm_ano'])), reverse=True),
                'pcd_count': pcd_count,
                'stores': stores_raw,
                'cargos': sorted(list(cargos_set)),
                'employees': employees
            }
            self._send_json(response_data)

        elif path in ['/api/users', '/api/users.py']:
            users_raw = query_d1('SELECT id, nome, email, role, stores, must_change_password FROM users;')
            users = []
            for u in users_raw:
                try:
                    st = json.loads(u.get('stores') or '["ALL"]')
                except:
                    st = ['ALL']
                users.append({
                    'id': u.get('id'),
                    'nome': u.get('nome'),
                    'email': u.get('email'),
                    'role': u.get('role'),
                    'stores': st,
                    'must_change_password': bool(u.get('must_change_password', 1))
                })
            self._send_json(users)

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
            
            # Direct Cloudflare D1 authentication
            users_raw = query_d1('SELECT * FROM users;')
            
            # Admin emergency fallback
            if (email == 'admin@leomadeiras.com.br' and senha == 'admin') or (email == 'admin' and senha == 'admin'):
                return self._send_json({
                    'success': True,
                    'must_change_password': False,
                    'user': {
                        'id': 'usr_admin',
                        'nome': 'Neto Cerasi (Admin)',
                        'email': 'admin@leomadeiras.com.br',
                        'role': 'ADMIN',
                        'stores': ['ALL'],
                        'must_change_password': False
                    }
                })

            for u in users_raw:
                if u.get('email', '').strip().lower() == email and str(u.get('senha', '')).strip() == senha:
                    try:
                        stores_list = json.loads(u.get('stores') or '["ALL"]')
                    except:
                        stores_list = ['ALL']
                    
                    must_change = bool(u.get('must_change_password', 1))
                    
                    # If must_change_password, require change before allowing full session
                    return self._send_json({
                        'success': True,
                        'must_change_password': must_change,
                        'user': {
                            'id': u.get('id'),
                            'nome': u.get('nome'),
                            'email': u.get('email'),
                            'role': u.get('role'),
                            'stores': stores_list,
                            'must_change_password': must_change
                        }
                    })

            return self._send_json({'success': False, 'message': 'E-mail ou senha incorretos.'}, status=401)

        elif path in ['/api/change-password', '/api/change-password.py']:
            email = payload.get('email', '').strip().lower()
            nova_senha = payload.get('nova_senha', '').strip()
            senha_atual = payload.get('senha_atual', '').strip()
            
            if not email or not nova_senha:
                return self._send_json({'success': False, 'message': 'Dados incompletos.'}, status=400)
            
            if len(nova_senha) < 4:
                return self._send_json({'success': False, 'message': 'A nova senha deve ter no mínimo 4 caracteres.'}, status=400)

            # Verify current password
            users_raw = query_d1('SELECT * FROM users WHERE LOWER(email) = ?;', [email])
            if not users_raw:
                return self._send_json({'success': False, 'message': 'Usuário não encontrado.'}, status=404)
            
            u = users_raw[0]
            if senha_atual and str(u.get('senha', '')).strip() != senha_atual:
                return self._send_json({'success': False, 'message': 'Senha atual incorreta.'}, status=401)

            # Update password and clear must_change_password flag
            query_d1('UPDATE users SET senha = ?, must_change_password = 0 WHERE id = ?;', [nova_senha, u.get('id')])
            
            try:
                stores_list = json.loads(u.get('stores') or '["ALL"]')
            except:
                stores_list = ['ALL']

            return self._send_json({
                'success': True,
                'message': 'Senha alterada com sucesso!',
                'user': {
                    'id': u.get('id'),
                    'nome': u.get('nome'),
                    'email': u.get('email'),
                    'role': u.get('role'),
                    'stores': stores_list,
                    'must_change_password': False
                }
            })

        elif path in ['/api/employees/add', '/api/employees/add.py', '/api/employees', '/api/employees.py']:
            emp = payload
            emp_id = emp.get('id') or f"emp_{int(datetime.datetime.now().timestamp())}"
            sql = '''INSERT OR REPLACE INTO employees 
                     (id, loja_num, nome_loja, matricula, nome, status, dt_desligamento, lider_direto, cpf, dt_admissao, adm_ano, adm_mes, adm_dia, raca_etnia, instrucao, pcd, cargo, area, dt_nascimento, idade, sexo, email, eh_mae_pai, qtd_filhos, filhos_json)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);'''
            
            dt_adm = str(emp.get('dt_admissao', ''))
            adm_ano, adm_mes, adm_dia = '', '', ''
            if dt_adm:
                parts = dt_adm.replace('-', '/').replace('.', '/').split('/')
                if len(parts) == 3:
                    adm_dia, adm_mes, adm_ano = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            
            params = [
                emp_id, str(emp.get('loja_num', '')), emp.get('nome_loja', ''), emp.get('matricula', ''),
                emp.get('nome', ''), emp.get('status', 'ATIVO'), emp.get('dt_desligamento', ''),
                emp.get('lider_direto', ''), emp.get('cpf', ''), dt_adm,
                adm_ano, adm_mes, adm_dia,
                emp.get('raca_etnia', 'NÃO INFORMADO'), emp.get('instrucao', ''), emp.get('pcd', 'NÃO'),
                emp.get('cargo', ''), emp.get('area', ''), emp.get('dt_nascimento', ''),
                int(emp.get('idade') or 0), emp.get('sexo', ''), emp.get('email', ''),
                emp.get('eh_mae_pai', 'NÃO'), len(emp.get('filhos', [])), json.dumps(emp.get('filhos', []))
            ]
            query_d1(sql, params)
            return self._send_json({'success': True, 'employee': emp})

        elif path in ['/api/users/save', '/api/users/save.py', '/api/users', '/api/users.py']:
            u = payload
            u_id = u.get('id') or f"usr_{int(datetime.datetime.now().timestamp())}"
            # Check if existing user or new user
            existing = query_d1('SELECT * FROM users WHERE id = ?;', [u_id])
            if existing:
                # If editing, only update senha if provided
                if u.get('senha'):
                    sql = '''UPDATE users SET nome = ?, email = ?, senha = ?, role = ?, stores = ?, must_change_password = ? WHERE id = ?;'''
                    params = [u.get('nome', ''), u.get('email', ''), u.get('senha', ''), u.get('role', 'USER'), json.dumps(u.get('stores', [])), 1 if u.get('must_change_password') else 0, u_id]
                else:
                    sql = '''UPDATE users SET nome = ?, email = ?, role = ?, stores = ?, must_change_password = ? WHERE id = ?;'''
                    params = [u.get('nome', ''), u.get('email', ''), u.get('role', 'USER'), json.dumps(u.get('stores', [])), 1 if u.get('must_change_password') else 0, u_id]
            else:
                sql = '''INSERT INTO users (id, nome, email, senha, role, stores, must_change_password) VALUES (?, ?, ?, ?, ?, ?, ?);'''
                params = [u_id, u.get('nome', ''), u.get('email', ''), u.get('senha', '1234'), u.get('role', 'USER'), json.dumps(u.get('stores', [])), 1]
            
            query_d1(sql, params)
            return self._send_json({'success': True, 'user': u})

        elif path in ['/api/users/delete', '/api/users/delete.py']:
            u_id = payload.get('id')
            if u_id:
                query_d1('DELETE FROM users WHERE id = ?;', [u_id])
            return self._send_json({'success': True})

        else:
            self._send_json({'error': 'Not found'}, status=404)
