"""
report_generator.py — Gera um relatório HTML standalone com todos os leads.
O arquivo é completamente autossuficiente: CSS + JS + dados embutidos.
Pode ser enviado por WhatsApp, email ou Drive — abre direto no browser.
"""

import json
from datetime import datetime


def gerar_relatorio_html(leads: list[dict], titulo: str = "OAB Lead Qualifier") -> str:
    """
    Retorna uma string com o HTML completo do relatório.
    Todos os dados, estilos e scripts são embutidos no arquivo.
    """
    leads_json = json.dumps(leads, ensure_ascii=False, default=str)
    data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    total = len(leads)
    quentes = sum(1 for l in leads if "Quente" in str(l.get("classificacao", "")))
    mornos = sum(1 for l in leads if "Morno" in str(l.get("classificacao", "")))
    frios = sum(1 for l in leads if "Frio" in str(l.get("classificacao", "")))
    com_contato = sum(
        1 for l in leads
        if l.get("phone_full") or l.get("phone_from_bio") or l.get("email")
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo} — Relatório de Leads</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', sans-serif;
    background: #0D1B2A;
    color: #F1F5F9;
    min-height: 100vh;
    padding: 0 0 60px;
  }}

  /* ── Header ── */
  .header {{
    background: #0A1628;
    border-bottom: 1px solid #1E3050;
    padding: 20px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  .header-left {{ display: flex; align-items: center; gap: 12px; }}
  .header-logo {{ font-size: 1.6rem; }}
  .header-title {{ font-size: 1.25rem; font-weight: 800; color: #F1F5F9; letter-spacing: -0.3px; }}
  .header-sub {{ font-size: 12px; color: #64748B; margin-top: 2px; }}
  .header-badge {{
    background: #162032;
    border: 1px solid #2D4A6E;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    color: #94A3B8;
  }}

  /* ── Layout ── */
  .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px 0; }}

  /* ── Métricas ── */
  .metrics {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }}
  @media (max-width: 768px) {{ .metrics {{ grid-template-columns: repeat(2, 1fr); }} }}
  .metric-card {{
    background: #162032;
    border: 1px solid #2D4A6E;
    border-radius: 12px;
    padding: 16px 20px;
    transition: border-color 0.2s;
  }}
  .metric-card:hover {{ border-color: #F59E0B; }}
  .metric-label {{ font-size: 12px; color: #94A3B8; font-weight: 500; margin-bottom: 6px; }}
  .metric-value {{ font-size: 2rem; font-weight: 700; color: #F1F5F9; }}

  /* ── Filtros ── */
  .filters {{
    background: #162032;
    border: 1px solid #2D4A6E;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
  }}
  .filter-group {{ display: flex; flex-direction: column; gap: 4px; }}
  .filter-label {{ font-size: 11px; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
  select, input[type="text"] {{
    background: #0D1B2A;
    border: 1px solid #2D4A6E;
    border-radius: 8px;
    color: #F1F5F9;
    padding: 7px 12px;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    outline: none;
    cursor: pointer;
    transition: border-color 0.2s;
  }}
  select:focus, input[type="text"]:focus {{ border-color: #F59E0B; }}
  .filter-check {{ display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 13px; color: #F1F5F9; }}
  .filter-check input {{ accent-color: #F59E0B; width: 15px; height: 15px; cursor: pointer; }}
  .filter-count {{ font-size: 12px; color: #64748B; margin-left: auto; align-self: flex-end; }}

  /* ── Cards ── */
  .leads-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .lead-card {{
    background: #162032;
    border: 1px solid #2D4A6E;
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.15s;
  }}
  .lead-card:hover {{ border-color: #3D6A9E; }}
  .lead-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    cursor: pointer;
    user-select: none;
    gap: 12px;
  }}
  .lead-header-left {{ display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }}
  .cls-badge {{
    font-size: 13px;
    font-weight: 700;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .cls-quente {{ color: #EF4444; }}
  .cls-morno  {{ color: #F59E0B; }}
  .cls-frio   {{ color: #3B82F6; }}
  .lead-name  {{ font-weight: 600; color: #F1F5F9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .lead-meta  {{ font-size: 12px; color: #64748B; white-space: nowrap; }}
  .score-pill {{
    background: #1E3050;
    border: 1px solid #2D4A6E;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 700;
    color: #F59E0B;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .chevron {{
    color: #64748B;
    font-size: 16px;
    transition: transform 0.2s;
    flex-shrink: 0;
  }}
  .lead-card.open .chevron {{ transform: rotate(180deg); }}

  /* ── Body do card ── */
  .lead-body {{
    display: none;
    border-top: 1px solid #1E3050;
    padding: 20px;
  }}
  .lead-card.open .lead-body {{ display: block; }}

  .lead-top {{ display: flex; align-items: flex-start; gap: 16px; margin-bottom: 16px; }}
  .avatar {{
    width: 72px;
    height: 72px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #2D4A6E;
    flex-shrink: 0;
    background: #1E3050;
  }}
  .avatar-initial {{
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: #1E3050;
    border: 2px solid #2D4A6E;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    font-weight: 700;
    color: #F59E0B;
    flex-shrink: 0;
  }}
  .lead-info-full h3 {{ font-size: 1.1rem; font-weight: 700; color: #F1F5F9; margin-bottom: 4px; }}
  .lead-info-full p {{ font-size: 13px; color: #94A3B8; }}

  .divider {{ border: none; border-top: 1px solid #1E3050; margin: 16px 0; }}

  /* ── Dados estruturados ── */
  .data-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }}
  @media (max-width: 640px) {{ .data-grid {{ grid-template-columns: 1fr; }} }}
  .data-section label {{ display: block; font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
  .data-section p {{ font-size: 13px; color: #F1F5F9; font-weight: 500; }}
  .data-section small {{ font-size: 12px; color: #64748B; }}

  /* ── Contatos ── */
  .contacts {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; align-items: center; }}
  .contact-info {{ font-size: 13px; color: #94A3B8; }}
  .contact-info strong {{ color: #F59E0B; }}
  .btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    background: #1E3050;
    color: #F1F5F9;
    border: 1px solid #2D4A6E;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .btn:hover {{ background: #F59E0B; color: #0A1628; border-color: #F59E0B; }}
  .btn-group {{ display: flex; flex-wrap: wrap; gap: 8px; }}

  /* ── Insight ── */
  .insight {{
    background: #111E30;
    border-left: 3px solid #F59E0B;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    font-size: 13px;
    color: #CBD5E1;
    line-height: 1.5;
  }}

  /* ── Sem resultados ── */
  .empty {{ text-align: center; padding: 60px 20px; color: #64748B; }}
  .empty h3 {{ font-size: 1.2rem; margin-bottom: 8px; }}

  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: #0D1B2A; }}
  ::-webkit-scrollbar-thumb {{ background: #2D4A6E; border-radius: 3px; }}
</style>
</head>
<body>

<header class="header">
  <div class="header-left">
    <span class="header-logo">⚖️</span>
    <div>
      <div class="header-title">OAB Lead Qualifier</div>
      <div class="header-sub">Relatório gerado em {data_geracao}</div>
    </div>
  </div>
  <div class="header-badge">{total} leads qualificados</div>
</header>

<div class="container">

  <!-- Métricas -->
  <div class="metrics">
    <div class="metric-card">
      <div class="metric-label">Total</div>
      <div class="metric-value" id="cnt-total">{total}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">🔥 Quentes</div>
      <div class="metric-value" style="color:#EF4444" id="cnt-quentes">{quentes}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">🟡 Mornos</div>
      <div class="metric-value" style="color:#F59E0B" id="cnt-mornos">{mornos}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">❄️ Frios</div>
      <div class="metric-value" style="color:#3B82F6" id="cnt-frios">{frios}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">📱 Com contato</div>
      <div class="metric-value" id="cnt-contato">{com_contato}</div>
    </div>
  </div>

  <!-- Filtros -->
  <div class="filters">
    <div class="filter-group">
      <span class="filter-label">Classificação</span>
      <select id="filtro-cls" onchange="filtrar()">
        <option value="">Todos</option>
        <option value="Quente">🔥 Quentes</option>
        <option value="Morno">🟡 Mornos</option>
        <option value="Frio">❄️ Frios</option>
      </select>
    </div>
    <div class="filter-group">
      <span class="filter-label">Nicho</span>
      <select id="filtro-nicho" onchange="filtrar()"></select>
    </div>
    <div class="filter-group">
      <span class="filter-label">Buscar</span>
      <input type="text" id="filtro-busca" placeholder="Nome ou @username..." oninput="filtrar()" style="min-width:200px">
    </div>
    <label class="filter-check">
      <input type="checkbox" id="filtro-email" onchange="filtrar()"> Com email
    </label>
    <label class="filter-check">
      <input type="checkbox" id="filtro-fone" onchange="filtrar()"> Com telefone
    </label>
    <label class="filter-check">
      <input type="checkbox" id="filtro-site" onchange="filtrar()"> Com site
    </label>
    <span class="filter-count" id="filter-count"></span>
  </div>

  <!-- Lista de leads -->
  <div class="leads-list" id="leads-container"></div>
  <div class="empty" id="empty-state" style="display:none">
    <h3>Nenhum lead encontrado</h3>
    <p>Tente ajustar os filtros.</p>
  </div>

</div>

<script>
const LEADS = {leads_json};

// Preencher filtro de nicho
const nichos = [...new Set(LEADS.map(l => l.nicho).filter(Boolean))].sort();
const selectNicho = document.getElementById('filtro-nicho');
selectNicho.innerHTML = '<option value="">Todos</option>' +
  nichos.map(n => `<option value="${{n}}">${{n}}</option>`).join('');

function clsClass(cls) {{
  if (cls && cls.includes('Quente')) return 'cls-quente';
  if (cls && cls.includes('Morno'))  return 'cls-morno';
  return 'cls-frio';
}}

function avatarHtml(lead) {{
  const initial = ((lead.full_name || lead.username || '?')[0] || '?').toUpperCase();
  const fallback = `<div class="avatar-initial">${{initial}}</div>`;
  if (!lead.avatar_url || lead.avatar_url === 'nan' || lead.avatar_url === 'None') return fallback;
  return `<img class="avatar" src="${{lead.avatar_url}}"
    onerror="this.outerHTML='${{fallback.replace(/'/g, "\\'")}}'">`;
}}

function phoneClean(p) {{
  return p ? String(p).replace(/\\D/g, '') : '';
}}

function renderCard(lead, idx) {{
  const cls = lead.classificacao || '';
  const score = lead.score || 0;
  const phone = lead.phone_full || lead.phone_from_bio || '';
  const email = lead.email || '';
  const wa = phone ? `https://wa.me/${{phoneClean(phone)}}` : '';
  const ig = lead.profile_url || `https://instagram.com/${{lead.username || ''}}`;

  const oabInfo = lead.oab_encontrado
    ? `<p>${{lead.oab_numero || ''}} ${{lead.oab_seccional || ''}} — ${{lead.oab_situacao || ''}}</p>
       ${{lead.oab_anos_ativo != null ? `<small>Inscrito há ${{Math.round(lead.oab_anos_ativo)}} ano(s)</small>` : ''}}`
    : '<small>Não encontrado</small>';

  const cnpjInfo = lead.cnpj_numero
    ? `<p>${{lead.cnpj_razao_social || lead.cnpj_numero}}</p><small>${{lead.cnpj_situacao || ''}}</small>`
    : '<small>Não encontrado</small>';

  const siteInfo = lead.site_encontrado
    ? `<p><a href="${{lead.site_url}}" target="_blank" style="color:#F59E0B">${{(lead.site_url||'').slice(0,35)}}...</a></p>
       <small>${{[lead.has_fb_pixel && 'Pixel FB', lead.has_ga && 'GA/GTM'].filter(Boolean).join(' · ') || '⚠️ Sem rastreamento'}}</small>`
    : '<small>Não encontrado</small>';

  return `
<div class="lead-card" id="card-${{idx}}">
  <div class="lead-header" onclick="toggle(${{idx}})">
    <div class="lead-header-left">
      <span class="cls-badge ${{clsClass(cls)}}">${{cls}}</span>
      <span class="lead-name">${{lead.full_name || lead.username || ''}}</span>
      <span class="lead-meta">@${{lead.username || ''}} · ${{lead.nicho || 'Geral'}}</span>
    </div>
    <span class="score-pill">Score ${{score}}/100</span>
    <span class="chevron">▾</span>
  </div>
  <div class="lead-body">
    <div class="lead-top">
      ${{avatarHtml(lead)}}
      <div class="lead-info-full">
        <h3>${{lead.full_name || lead.username || ''}}</h3>
        <p>@${{lead.username || ''}} · ⚖️ ${{lead.nicho || 'Geral'}} · ${{(lead.followers||0).toLocaleString('pt-BR')}} seguidores</p>
      </div>
    </div>
    <hr class="divider">
    <div class="data-grid">
      <div class="data-section"><label>OAB</label>${{oabInfo}}</div>
      <div class="data-section"><label>CNPJ</label>${{cnpjInfo}}</div>
      <div class="data-section"><label>Site</label>${{siteInfo}}</div>
    </div>
    <hr class="divider">
    <div class="contacts">
      ${{phone ? `<span class="contact-info">📱 <strong>${{phone}}</strong></span>` : ''}}
      ${{email ? `<span class="contact-info">✉️ <strong>${{email}}</strong></span>` : ''}}
    </div>
    <div class="btn-group">
      ${{wa ? `<a class="btn" href="${{wa}}" target="_blank">💬 WhatsApp</a>` : ''}}
      ${{email ? `<a class="btn" href="mailto:${{email}}">✉️ Email</a>` : ''}}
      <a class="btn" href="${{ig}}" target="_blank">📸 Instagram</a>
    </div>
    ${{lead.insight ? `<hr class="divider"><div class="insight">💡 ${{lead.insight}}</div>` : ''}}
  </div>
</div>`;
}}

function toggle(idx) {{
  const card = document.getElementById('card-' + idx);
  card.classList.toggle('open');
}}

let visibleIds = LEADS.map((_, i) => i);

function filtrar() {{
  const cls    = document.getElementById('filtro-cls').value;
  const nicho  = document.getElementById('filtro-nicho').value;
  const busca  = document.getElementById('filtro-busca').value.toLowerCase();
  const email  = document.getElementById('filtro-email').checked;
  const fone   = document.getElementById('filtro-fone').checked;
  const site   = document.getElementById('filtro-site').checked;

  visibleIds = [];
  LEADS.forEach((l, i) => {{
    if (cls   && !(l.classificacao||'').includes(cls)) return;
    if (nicho && l.nicho !== nicho) return;
    if (email && !l.email) return;
    if (fone  && !l.phone_full && !l.phone_from_bio) return;
    if (site  && !l.site_encontrado) return;
    if (busca && !(l.full_name||'').toLowerCase().includes(busca)
              && !(l.username||'').toLowerCase().includes(busca)) return;
    visibleIds.push(i);
  }});

  renderList();
}}

function renderList() {{
  const container = document.getElementById('leads-container');
  const empty     = document.getElementById('empty-state');

  if (visibleIds.length === 0) {{
    container.innerHTML = '';
    empty.style.display = 'block';
  }} else {{
    empty.style.display = 'none';
    container.innerHTML = visibleIds.map(i => renderCard(LEADS[i], i)).join('');
  }}
  document.getElementById('filter-count').textContent =
    visibleIds.length + ' de ' + LEADS.length + ' leads';
}}

// Render inicial (ordenado por score desc)
LEADS.sort((a, b) => (b.score || 0) - (a.score || 0));
renderList();
</script>
</body>
</html>"""
