import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
from datetime import datetime
import os

# --- 1. CONFIGURAÇÃO E IDENTIDADE VISUAL ---
st.set_page_config(page_title="TecPulver Brasil", layout="centered", page_icon="🟢")

st.markdown("""
    <style>
    .icon-sprayer {
    background: #2e7d32; 
    padding: 12px; /* Ajustado para caber no cabeçalho */
    border-radius: 50%; 
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-right: 15px; 
    box-shadow: 0 0 20px rgba(46, 125, 50, 0.6);
    border: 2px solid rgba(255,255,255,0.2);
    font-size: 1.5rem;
}
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.9)), 
                    url('https://images.unsplash.com/photo-1560493676-04071c5f467b?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80');
        background-size: cover;
        background-attachment: fixed;
    }
    div.stButton > button {
        width: 100% !important;
        background-color: #4CAF50 !important; color: white !important;
        font-weight: 800 !important; border-radius: 10px !important;
        height: 3.5em !important; border: none !important;
    }
    /* Botão de sair com cor diferente */
    div[data-testid="stButton"].sair-btn > button {
        background-color: #c0392b !important;
    }
    .stSelectbox label, .stRadio label, p, h3, h4, span, h1, h2 { color: #ffffff !important; font-weight: 600 !important; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE ---
def registrar_usuario_csv(nome, email):
    arquivo = 'usuarios_cadastrados.csv'
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    novo_log = pd.DataFrame([[data_hora, nome, email]], columns=['Data', 'Nome', 'Email'])
    if not os.path.isfile(arquivo):
        novo_log.to_csv(arquivo, index=False, sep=';', encoding='utf-8-sig')
    else:
        novo_log.to_csv(arquivo, mode='a', index=False, header=False, sep=';', encoding='utf-8-sig')

@st.cache_data
def carregar_produtos_turbo(classe):
    mapa = {
        "Herbicidas": "herbicidas.csv",
        "Fungicidas": "fungicidas.csv",
        "Inseticidas": "inseticidas.csv",
        "Reguladores": "reguladores.csv",
        
    }
    arquivo = mapa.get(classe)
    if arquivo and os.path.exists(arquivo):
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
            if not df.empty:
                return sorted(df.iloc[:, 0].dropna().unique().tolist())
            else:
                return ["Arquivo CSV está vazio"]
        except Exception:
            return [f"Erro na leitura: {arquivo}"]
    return [f"Arquivo {arquivo} não encontrado na pasta"]

def gerar_tabela_html(tabela_dados):
    linhas = ""
    for row in tabela_dados:
        horario, temp, umid, vento, status = row
        if status == "IDEAL":
            badge = '<span class="badge-ideal">✅ IDEAL</span>'
            tr_bg = "background-color: rgba(76,175,80,0.07);"
        else:
            badge = '<span class="badge-inadequado">❌ INADEQUADO</span>'
            tr_bg = ""

        linhas += f"""
        <tr style="{tr_bg}">
            <td><span class="horario-pill">{horario}</span></td>
            <td>🌡️ {temp}</td>
            <td>💧 {umid}</td>
            <td>💨 {vento}</td>
            <td>{badge}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
        body {{ margin: 0; padding: 0; background: transparent; font-family: 'Segoe UI', Arial, sans-serif; }}
        .tabela-horarios {{ width: 100%; border-collapse: collapse; border-radius: 12px; overflow: hidden; font-size: 0.93em; box-shadow: 0 4px 24px rgba(0,0,0,0.45); }}
        .tabela-horarios thead tr {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: #fff; text-align: center; font-weight: 700; font-size: 0.82em; letter-spacing: 0.06em; text-transform: uppercase; }}
        .tabela-horarios thead th {{ padding: 13px 10px; border-bottom: 2px solid #4CAF50; }}
        .tabela-horarios tbody tr {{ border-bottom: 1px solid rgba(255,255,255,0.07); background-color: #0f0f1a; }}
        .tabela-horarios tbody tr:nth-child(even) {{ background-color: #13132a; }}
        .tabela-horarios tbody tr:hover {{ background-color: rgba(76,175,80,0.13) !important; }}
        .tabela-horarios td {{ padding: 10px 12px; text-align: center; color: #dde1e7; font-weight: 500; }}
        .badge-ideal {{ background: linear-gradient(135deg, #1b5e20, #2e7d32); color: #a5d6a7; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.82em; border: 1px solid #4CAF50; display: inline-block; }}
        .badge-inadequado {{ background: linear-gradient(135deg, #7f1d1d, #b91c1c); color: #fca5a5; padding: 5px 14px; border-radius: 20px; font-weight: 700; font-size: 0.82em; border: 1px solid #ef4444; display: inline-block; }}
        .horario-pill {{ background: rgba(76,175,80,0.15); border: 1px solid rgba(76,175,80,0.35); border-radius: 8px; padding: 3px 11px; font-weight: 700; color: #a5d6a7; font-size: 0.91em; }}
    </style>
    </head><body>
    <table class="tabela-horarios">
        <thead><tr>
            <th>🕐 Horário</th><th>🌡️ Temperatura</th><th>💧 Umidade</th><th>💨 Vento</th><th>📊 Status</th>
        </tr></thead>
        <tbody>{linhas}</tbody>
    </table>
    </body></html>
    """
    return html

# --- 3. SISTEMA DE ACESSO COM PERSISTÊNCIA ---
if 'autenticado' not in st.session_state:
    params = st.query_params
    if params.get("u"):
        st.session_state.autenticado = True
        st.session_state.usuario_logado = params["u"]
    else:
        st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<h2 style='text-align:center;'>TecPulver Brasil</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Criar Conta"])

    with t1:
        e_in = st.text_input("E-mail:", key="e_login")
        s_in = st.text_input("Senha:", type="password")
        manter = st.checkbox("Manter-se conectado", value=True)
        if st.button("ACESSAR PLATAFORMA"):
            if e_in:
                st.session_state.autenticado = True
                st.session_state.usuario_logado = e_in.strip().lower()
                if manter:
                    st.query_params["u"] = e_in.strip().lower()
                st.rerun()

    with t2:
        n_cad = st.text_input("Nome:")
        e_cad = st.text_input("E-mail:", key="e_cad")
        if st.button("FINALIZAR CADASTRO"):
            if n_cad and e_cad:
                registrar_usuario_csv(n_cad, e_cad)
                st.session_state.autenticado = True
                st.session_state.usuario_logado = e_cad.strip().lower()
                st.query_params["u"] = e_cad.strip().lower()
                st.rerun()
    st.stop()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.usuario_logado}**")
    st.divider()
    if st.button("🚪 SAIR DA CONTA", key="sair_sidebar"):
        st.session_state.autenticado = False
        st.query_params.clear()
        st.rerun()

# --- 5. MODO GESTOR ---
if st.session_state.usuario_logado == "felipe_fgd_@hotmail.com":
    st.warning("🛠️ MODO GESTOR ATIVADO")
    if os.path.exists('usuarios_cadastrados.csv'):
        df_gestor = pd.read_csv('usuarios_cadastrados.csv', sep=';')
        st.download_button("📥 BAIXAR LISTA DE USUÁRIOS (CSV)", df_gestor.to_csv(index=False, sep=';', encoding='utf-8-sig'), "relatorio_usuarios.csv", "text/csv", use_container_width=True)
    st.divider()

# --- 6. CABEÇALHO COM SIMBOLOGIA DE PRECISÃO (SVG) E BOTÃO SAIR ---
# Usamos um container único para garantir que o HTML seja lido corretamente
header_container = st.container()

with header_container:
    col_titulo, col_sair = st.columns([4, 1])
    
    with col_titulo:
        # Definimos o HTML completo em uma variável separada
        html_cabecalho = f"""
        <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 5px;'>
            <svg width="45" height="45" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <path d="M 20 80 A 30 30 0 0 1 80 80" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
                <line x1="50" y1="15" x2="50" y2="60" stroke="white" stroke-width="8" stroke-linecap="round"/>
                <path d="M 50 82 L 35 62 L 65 62 Z" fill="white"/>
            </svg>
            <h1 style='margin: 0; padding: 0; font-size: 2.2rem; color: white; font-family: sans-serif; white-space: nowrap;'>
                TecPulver Brasil
            </h1>
        </div>
        <p style='color:#aaaaaa !important; font-size: 0.85em; margin: 0; margin-left: 60px;'>
            🛰️ Monitoramento Ativo: {st.session_state.usuario_logado}
        </p>
        """
        st.markdown(html_cabecalho, unsafe_allow_html=True)

    with col_sair:
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Sair", key="sair_topo"):
            st.session_state.autenticado = False
            st.query_params.clear()
            st.rerun()

st.divider()
# --- 7. FORMULÁRIO TÉCNICO ---
uf_sel = st.selectbox("📍 ESTADO (UF):",
                      options=["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"],
                      index=None, placeholder="Digite aqui...")

cidades = []
if uf_sel:
    try:
        res = requests.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sel}/municipios")
        cidades = sorted([m['nome'] for m in res.json()]) if res.status_code == 200 else []
    except:
        cidades = []

cid_sel = st.selectbox("🏙️ CIDADE:", options=cidades, index=None, placeholder="Digite aqui...", disabled=not uf_sel)

st.markdown("---")

classe_sel = st.selectbox("🧪 CLASSE QUÍMICA:", options=["Herbicidas","Fungicidas","Inseticidas","Reguladores"], index=None, placeholder="Digite aqui...")
opcoes_prod = carregar_produtos_turbo(classe_sel) if classe_sel else []
prod_sel = st.selectbox("📦 PRODUTO COMERCIAL:", options=opcoes_prod, index=None, placeholder="Digite aqui...", disabled=not classe_sel)
tipo_app = st.radio("🚜 MODALIDADE:", ["Terrestre", "Aérea"], horizontal=True)

st.divider()

# --- 8. EXECUÇÃO DA ANÁLISE ---
if st.button("VERIFICAR CONDIÇÕES AGORA", type="primary"):
    if uf_sel and cid_sel and prod_sel:
        try:
            cidade_url = cid_sel.replace(" ", "%20")
            geo_url = f"https://nominatim.openstreetmap.org/search?city={cidade_url}&state={uf_sel}&country=Brazil&format=json"
            headers = {'User-Agent': 'TecPulver-App-Felipe'}
            geo_res = requests.get(geo_url, headers=headers).json()

            if geo_res:
                lat, lon = geo_res[0]['lat'], geo_res[0]['lon']
                clima_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&forecast_days=2"
                res_clima = requests.get(clima_url).json()

                st.markdown(f"### 🛰️ Planejamento 24h: {cid_sel} - {uf_sel}")
                st.write(f"**Produto:** {prod_sel} | **Modalidade:** {tipo_app}")

                dados_horas = res_clima['hourly']
                hora_atual = datetime.now().hour
                tabela_dados = []

                for i in range(hora_atual, hora_atual + 24):
                    t = dados_horas['temperature_2m'][i]
                    u = dados_horas['relative_humidity_2m'][i]
                    v = dados_horas['wind_speed_10m'][i]
                    dt = (t * 0.75) - (u * 0.15)

                    status = "IDEAL" if (2.0 <= dt <= 8.0 and 2.0 <= v <= 10.0 and t < 30) else "INADEQUADO"
                    tabela_dados.append([f"{i % 24:02d}:00", f"{t:.1f}°C", f"{u:.0f}%", f"{v:.1f} km/h", status])

                html_tabela = gerar_tabela_html(tabela_dados)
                components.html(html_tabela, height=900, scrolling=True)

                ideais = sum(1 for r in tabela_dados if r[4] == "IDEAL")
                st.success(f"✅ {ideais} de 24 horários com condições IDEAIS para aplicação em {cid_sel}.")
            else:
                st.error("Erro ao localizar coordenadas da cidade.")
        except Exception as e:
            st.error("Erro na conexão meteorológica.")
    else:
        st.error("⚠️ Selecione Estado, Cidade e Produto primeiro.")
