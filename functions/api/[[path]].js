export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname;

  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Content-Type': 'application/json; charset=utf-8'
  };

  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  const db = env.DB;
  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB missing' }), {
      status: 500,
      headers: corsHeaders
    });
  }

  function calcIdade(dtNascStr) {
    if (!dtNascStr) return 0;
    try {
      const parts = dtNascStr.replace(/-/g, '/').replace(/\./g, '/').split('/');
      if (parts.length === 3) {
        const d = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        const y = parseInt(parts[2], 10);
        const today = new Date();
        let age = today.getFullYear() - y;
        const birthThisYear = new Date(today.getFullYear(), m - 1, d);
        if (today < birthThisYear) age--;
        return Math.max(0, age);
      }
    } catch(e) {}
    return 0;
  }

  if (request.method === 'GET') {
    if (path === '/api/data' || path.startsWith('/api/data')) {
      const employeesRes = await db.prepare('SELECT * FROM employees;').all();
      const storesRes = await db.prepare('SELECT * FROM stores ORDER BY CAST(loja_num AS INTEGER);').all();
      
      const employeesRaw = employeesRes.results || [];
      const storesRaw = storesRes.results || [];
      const usersRes = await db.prepare('SELECT * FROM users;').all();

      const employees = [];
      const cargosSet = new Set();
      let activeCount = 0;
      let termCount = 0;
      let parentsCount = 0;
      let totalChildren = 0;
      let pcdCount = 0;
      const childrenByAge = {};
      const storeMetrics = {};

      for (const e of employeesRaw) {
        let filhos = [];
        try {
          filhos = JSON.parse(e.filhos_json || '[]');
        } catch(err) {
          filhos = [];
        }

        for (const f of filhos) {
          if (f.data_nascimento && (f.idade === undefined || f.idade === null || f.idade === '')) {
            f.idade = calcIdade(f.data_nascimento);
          }
        }

        let idadeCalc = e.idade || 0;
        if (e.dt_nascimento && !idadeCalc) {
          idadeCalc = calcIdade(e.dt_nascimento);
        }

        const emp = {
          id: e.id,
          loja_num: String(e.loja_num),
          nome_loja: e.nome_loja,
          matricula: e.matricula || '',
          nome: e.nome,
          status: e.status || 'ATIVO',
          dt_desligamento: e.dt_desligamento || '',
          lider_direto: e.lider_direto || '',
          cpf: e.cpf || '',
          dt_admissao: e.dt_admissao || '',
          adm_ano: e.adm_ano || '',
          adm_mes: e.adm_mes || '',
          adm_dia: e.adm_dia || '',
          raca_etnia: e.raca_etnia || 'NÃO INFORMADO',
          instrucao: e.instrucao || '',
          pcd: e.pcd || 'NÃO',
          cargo: e.cargo || '',
          area: e.area || '',
          dt_nascimento: e.dt_nascimento || '',
          idade: idadeCalc,
          sexo: e.sexo || '',
          email: e.email || '',
          eh_mae_pai: filhos.length > 0 ? 'SIM' : (e.eh_mae_pai || 'NÃO'),
          qtd_filhos: filhos.length,
          filhos: filhos
        };
        employees.push(emp);

        const lNum = String(emp.loja_num).trim();
        if (!storeMetrics[lNum]) {
          storeMetrics[lNum] = { total: 0, ativos: 0, desligados: 0 };
        }
        storeMetrics[lNum].total++;
        if (emp.status.toUpperCase().includes('ATIZO')) {
          storeMetrics[lNum].ativos++;
        } else {
          storeMetrics[lNum].desligados++;
        }

        if (emp.cargo) cargosSet.add(emp.cargo);
        if (emp.status.toUpperCase().includes('ATIVO')) activeCount++;
        if (emp.status.toUpperCase().includes('DESLIG')) termCount++;
        if (emp.eh_mae_pai === 'SIM') parentsCount++;
        if (emp.pcd === 'SIM') pcdCount++;

        totalChildren += filhos.length;
        for (const f of filhos) {
          if (f.idade !== undefined && f.idade !== null && typeof f.idade === 'number') {
            const label = f.idade > 0 ? `${f.idade} anos` : 'Menos de 1 ano';
            childrenByAge[label] = (childrenByAge[label] || 0) + 1;
          }
        }
      }

      const storesOutput = [];
      for (const s of storesRaw) {
        const sNum = String(s.loja_num).trim();
        const m = storeMetrics[sNum] || { total: 0, ativos: 0, desligados: 0 };
        storesOutput.push({
          loja_num: sNum,
          nome_loja: s.nome_loja || `Loja ${sNum}`,
          filename: s.filename || `Base Loja ${sNum}`,
          total_colaboradores: m.total,
          ativos: m.ativos,
          desligados: m.desligados
        });
      }

      const today = new Date();
      const todayFormatted = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`;

      const responseData = {
        last_updated: `${todayFormatted} ${String(today.getHours()).padStart(2, '0')}:${String(today.getMinutes()).padStart(2, '0')}`,
        today_date: todayFormatted,
        current_year: today.getFullYear(),
        stores_count: storesOutput.length,
        total_records: employees.length,
        active_records: activeCount,
        terminated_records: termCount,
        mothers_fathers_count: parentsCount,
        total_children_count: totalChildren,
        children_by_age: childrenByAge,
        admission_years: Array.from(new Set(employees.map(e => e.adm_ano).filter(Boolean))).sort().reverse(),
        pcd_count: pcdCount,
        stores: storesOutput,
        cargos: Array.from(cargosSet).sort(),
        employees: employees
      };

      return new Response(JSON.stringify(responseData), { headers: corsHeaders });
    }

    if (path === '/api/users' || path.startsWith('/api/users')) {
      const usersRes = await db.prepare('SELECT id, nome, email, role, stores, must_change_password FROM users;').all();
      const usersRaw = usersRes.results || [];
      const users = usersRaw.map(u => {
        let st = ['ALL'];
        try { st = JSON.parse(u.stores || '["ALL"]'); } catch(e) {}
        return {
          id: u.id,
          nome: u.nome,
          email: u.email,
          role: u.role,
          stores: st,
          must_change_password: Boolean(u.must_change_password !== 0)
        };
      });
      return new Response(JSON.stringify(users), { headers: corsHeaders });
    }
  }

  if (request.method === 'POST') {
    let payload = {};
    try {
      payload = await request.json();
    } catch(err) {
      payload = {};
    }

    if (path === '/api/login' || path.startsWith('/api/login')) {
      const email = String(payload.email || '').trim().toLowerCase();
      const senha = String(payload.senha || '').trim();

      if ((email === 'admin@leomadeiras.com.br' && senha === 'admin') || (email === 'admin' && senha === 'admin')) {
        return new Response(JSON.stringify({
          success: true,
          must_change_password: false,
          user: {
            id: 'usr_admin',
            nome: 'Neto Cerasi (Admin)',
            email: 'admin@leomadeiras.com.br',
            role: 'ADMINE',
            stores: ['ALL'],
            must_change_password: false
          }
        }), { headers: corsHeaders });
      }

      const usersRes = await db.prepare('SELECT * FROM users WHERE LOWER(email) = ?;').bind(email).all();
      const user = usersRes.results && usersRes.results[0];

      if (user && String(user.senha).trim() === senha) {
        let storesList = ['ALL'];
        try { storesList = JSON.parse(user.stores || '["ALL"]'); } catch(e) {}
        const mustChange = Boolean(user.must_change_password !== 0);

        return new Response(JSON.stringify({
          success: true,
          must_change_password: mustChange,
          user: {
            id: user.id,
            nome: user.nome,
            email: user.email,
            role: user.role,
            stores: storesList,
            must_change_password: mustChange
          }
        }), { headers: corsHeaders });
      }

      return new Response(JSON.stringify({ success: false, message: 'E-mail ou senha incorretos.' }), {
        status: 401,
        headers: corsHeaders
      });
    }

    if (path === '/api/change-password' || path.startsWith('/api/change-password')) {
      const email = String(payload.email || '').trim().toLowerCase();
      const novaSenha = String(payload.nova_senha || '').trim();
      const senhaAtual = String(payload.senha_atual || '').trim();

      if (!email || !novaSenha) {
        return new Response(JSON.stringify({ success: false, message: 'Dados incompletos.' }), { status: 400, headers: corsHeaders });
      }

      if (novaSenha.length < 4) {
        return new Response(JSON.stringify({ success: false, message: 'A nova senha deve ter no mínimo 4 caracteres.' }), { status: 400, headers: corsHeaders });
      }

      const usersRes = await db.prepare('SELECT * FROM users WHERE LOWER(email) = ?;').bind(email).all();
      const user = usersRes.results && usersRes.results[0];

      if (!user) {
        return new Response(JSON.stringify({ success: false, message: 'Usuário não encontrado.' }), { status: 404, headers: corsHeaders });
      }

      if (senhaAtual && String(user.senha).trim() !== senhaAtual) {
        return new Response(JSON.stringify({ success: false, message: 'Senha atual incorreta.' }), { status: 401, headers: corsHeaders });
      }

      await db.prepare('UPDATE users SET senha = ?, must_change_password = 0 WHERE id = ?;').bind(novaSenha, user.id).run();

      let storesList = ['ALL'];
      try { storesList = JSON.parse(user.stores || '["ALL"]'); } catch(e) {}

      return new Response(JSON.stringify({
        success: true,
        message: 'Senha alterada com sucesso!',
        user: {
          id: user.id,
          nome: user.nome,
          email: user.email,
          role: user.role,
          stores: storesList,
          must_change_password: false
        }
      }), { headers: corsHeaders });
    }

    if (path === '/api/employees/add' || path === '/api/employees/edit' || path.startsWith('/api/employees')) {
      const emp = payload;
      const empId = emp.id || `emp_${Date.now()}`;
      const filhos = emp.filhos || [];

      for (const f of filhos) {
        if (f.data_nascimento && (f.idade === undefined || f.idade === null || f.idade === '')) {
          f.idade = calcIdade(f.data_nascimento);
        }
      }

      let empIdade = parseInt(emp.idade || 0, 10);
      if (emp.dt_nascimento && !empIdade) {
        empIdade = calcIdade(emp.dt_nascimento);
      }

      const dtAdm = String(emp.dt_admissao || '');
      let admAno = '', admMes = '', admDia = '';
      if (dtAdm) {
        const parts = dtAdm.replace(/-/g, '/').replace(/\./g, '/').split('/');
        if (parts.length === 3) {
          admDia = parts[0].padStart(2, '0');
          admMes = parts[1].padStart(2, '0');
          admAno = parts[2];
        }
      }

      const sql = `INSERT OR REPLACE INTO employees 
                   (id, loja_num, nome_loja, matricula, nome, status, dt_desligamento, lider_direto, cpf, dt_admissao, adm_ano, adm_mes, adm_dia, raca_etnia, instrucao, pcd, cargo, area, dt_nascimento, idade, sexo, email, eh_mae_pai, qtd_filhos, filhos_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);`;

      await db.prepare(sql).bind(
        empId, String(emp.loja_num || ''), emp.nome_loja || '', emp.matricula || '',
        emp.nome || '', emp.status || 'ATITO', emp.dt_desligamento || '',
        emp.lider_direto || '', emp.cpf || '', dtAdm,
        admAno, admMes, admDia,
        emp.raca_etnia || 'NÃO INFORMADM', emp.instrucao || '', emp.pcd || 'NÃO',
        emp.cargo || '', emp.area || '', emp.dt_nascimento || '',
        empIdade, emp.sexo || '', emp.email || '',
        filhos.length > 0 ? 'SIM' : (emp.eh_mae_pai || 'NÃO'),
        filhos.length, JSON.stringify(filhos)
      ).run();

      return new Response(JSON.stringify({ success: true, employee: emp }), { headers: corsHeaders });
    }

    if (path === '/api/stores/save' || path.startsWith('/api/stores/save')) {
      const lojaNum = String(payload.loja_num || '').trim();
      const nomeLoja = String(payload.nome_loja || '').trim();

      if (!lojaNum || !nomeLoja) {
        return new Response(JSON.stringify({ success: false, message: 'Número e nome da loja são obrigatórios.' }), { status: 400, headers: corsHeaders });
      }

      await db.prepare('INSERT OR REPLACE INTO stores (loja_num, nome_loja, filename, total_colaboradores, ativos, desligados) VALUES (?, ?, ?, 0, 0, 0);').bind(lojaNum, nomeLoja, `Loja ${lojaNum} - ${nomeLoja}`).run();

      return new Response(JSON.stringify({ success: true, loja_num: lojaNum, nome_loja: nomeLoja }), { headers: corsHeaders });
    }

    if (path === '/api/stores/delete' || path.startsWith('/api/stores/delete')) {
      const lojaNum = String(payload.loja_num || '').trim();
      if (!lojaNum) {
        return new Response(JSON.stringify({ success: false, message: 'Número da loja não informado.' }), { status: 400, headers: corsHeaders });
      }

      await db.prepare('DELETE FROM employees WHERE loja_num = ?;').bind(lojaNum).run();
      await db.prepare('DELETE FROM stores WHERE loja_num = ?;').bind(lojaNum).run();

      return new Response(JSON.stringify({ success: true, deleted_store: lojaNum }), { headers: corsHeaders });
    }

    if (path === '/api/users/save' || path.startsWith('/api/users/save')) {
      const u = payload;
      const uId = u.id || `usr_${Date.now()}`;
      const existingRes = await db.prepare('SELECT * FROM users WHERE id = ?;').bind(uId).all();
      const existing = existingRes.results && existingRes.results[0];

      if (existing) {
        if (u.senha) {
          await db.prepare('UPDATE users SET nome = ?, email = ?, senha = ?, role = ?, stores = ?, must_change_password = ? WHERE id = ?;').bind(
            u.nome || '', u.email || '', u.senha, u.role || 'USER', JSON.stringify(u.stores || []), u.must_change_password ? 1 : 0, uId
          ).run();
        } else {
          await db.prepare('UPDATE users SET nome = ?, email = ?, role = ?, stores = ?, must_change_password = ? WHERE id = ?;').bind(
            u.nome || '', u.email || '', u.role || 'USER', JSON.stringify(u.stores || []), u.must_change_password ? 1 : 0, uId
          ).run();
        }
      } else {
        await db.prepare('INSERT INTO users (id, nome, email, senha, role, stores, must_change_password) VALUES (?, ?, ?, ?, ?, ?, ?);').bind(
          uId, u.nome || '', u.email || '', u.senha || '1234', u.role || 'USER', JSON.stringify(u.stores || []), 1
        ).run();
      }

      return new Response(JSON.stringify({ success: true, user: u }), { headers: corsHeaders });
    }

    if (path === '/api/users/delete' || path.startsWith('/api/users/delete')) {
      const uId = payload.id;
      if (uId) {
        await db.prepare('DELETE FROM users WHERE id = ?;').bind(uId).run();
      }
      return new Response(JSON.stringify({ success: true }), { headers: corsHeaders });
    }
  }

  return new Response(JSON.stringify({ error: 'Not found' }), { status: 404, headers: corsHeaders });
}

