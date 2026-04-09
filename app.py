import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import os
import streamlit as st
import streamlit.components.v1 as components
import requests
import math
import hashlib
import secrets
import smtplib
import toml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from urllib.parse import unquote  # ← MOVIDO PARA O TOPO
import gspread.exceptions
from gspread.exceptions import CellNotFound 
def gerar_hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# --- FUNÇÃO DE CONEXÃO MESTRA ---
# --- FUNÇÃO DE CONEXÃO MESTRA ---
def conectar_planilha():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    # Usando o ID da planilha (mais rápido e à prova de erros de nome)
    id_da_planilha = "1-ra4aDcLc_UDokHszNUGXRRWNUE9hQfuwsD18HPAy0Y"
    
    spreadsheet = client.open_by_key(id_da_planilha)
    sheet = spreadsheet.get_worksheet(0) # Pega a primeira aba
    return sheet
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="TecPulver Brasil", layout="centered", page_icon="🟢")

# INJEÇÃO OCULTA DE METADADOS PWA
components.html("""
    <script>
        var meta1 = document.createElement('meta');
        meta1.name = "apple-mobile-web-app-capable"; meta1.content = "yes";
        document.getElementsByTagName('head')[0].appendChild(meta1);
        var meta2 = document.createElement('meta');
        meta2.name = "mobile-web-app-capable"; meta2.content = "yes";
        document.getElementsByTagName('head')[0].appendChild(meta2);
        var meta3 = document.createElement('meta');
        meta3.name = "apple-mobile-web-app-status-bar-style"; meta3.content = "black-translucent";
        document.getElementsByTagName('head')[0].appendChild(meta3);
        var link = document.createElement('link');
        link.rel = "apple-touch-icon"; link.href = "https://raw.githubusercontent.com/felipe/tecpulver/main/logo.png";
        document.getElementsByTagName('head')[0].appendChild(link);
    </script>
""", height=0, width=0)

st.markdown("""
    <style>
    .icon-sprayer {
        background: #2e7d32; padding: 12px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        margin-right: 15px; box-shadow: 0 0 20px rgba(46, 125, 50, 0.6);
        border: 2px solid rgba(255,255,255,0.2); font-size: 1.5rem;
    }
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.9), rgba(0,0,0,0.9)),
                    url('https://images.unsplash.com/photo-1560493676-04071c5f467b?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80');
        background-size: cover; background-attachment: fixed;
    }
    div.stButton > button {
        width: 100% !important; background-color: #4CAF50 !important; color: white !important;
        font-weight: 800 !important; border-radius: 10px !important;
        height: 3.5em !important; border: none !important;
    }
    div[data-testid="stButton"].sair-btn > button { background-color: #c0392b !important; }
    .stSelectbox label, .stRadio label, p, h3, h4, span, h1, h2 { color: #ffffff !important; font-weight: 600 !important; }
    #MainMenu, footer, header {visibility: hidden !important;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO PARA GRAVAR A NOVA SENHA ---
def salvar_nova_senha(email, nova_senha_hash):
    try:
        sheet = conectar_planilha()
        # Busca o e-mail (coluna Email)
        cell = sheet.find(email.strip().lower())
        if not cell:
            st.error("E-mail não encontrado na planilha.")
            return False
        # SenhaHash está na COLUNA 4 (D) — ajuste se necessário
        sheet.update_cell(cell.row, 4, nova_senha_hash)
        # Limpa o token na COLUNA 5 (E) para invalidar o link
        sheet.update_cell(cell.row, 5, "")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- FUNÇÃO PARA LER USUÁRIOS ---
def carregar_usuarios_planilha():
    try:
        sheet = conectar_planilha()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

# --- INICIALIZAÇÃO DO ESTADO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

# ============================================================
# INTERCEPTADOR DE RESET DE SENHA — TOPO DO APP
# Roda ANTES de qualquer outra coisa se o parâmetro existir
# ============================================================
_params = st.query_params
_reset_token = _params.get("reset_token", "").strip()
# unquote decodifica %40 → @ e remove espaços extras
_reset_email = unquote(_params.get("email", "")).strip().lower()

if _reset_token and _reset_email:
    st.markdown("<h2 style='text-align:center; color:white;'>🔑 Redefinir Senha</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#aaa;'>Conta: <b>{_reset_email}</b></p>", unsafe_allow_html=True)

    token_valido = False

    try:
        sheet = conectar_planilha()

        # Procura o TOKEN na planilha (coluna 5 / E)
        cell_token = sheet.find(_reset_token)

        if cell_token:
            # Pega o e-mail na COLUNA 3 (C) da mesma linha
            # ⚠️ Ajuste o número da coluna conforme sua planilha real
            email_na_planilha = str(sheet.cell(cell_token.row, 3).value).strip().lower()

            if email_na_planilha == _reset_email:
                token_valido = True
            else:
                st.error(f"❌ Token não pertence a este e-mail. (planilha={email_na_planilha})")
        else:
            st.error("❌ Token não encontrado. Pode já ter sido usado ou expirado.")

    except Exception as e:
        st.error(f"❌ Erro ao validar token: {e}")

    if token_valido:
        nova1 = st.text_input("Nova senha:", type="password", placeholder="Mínimo 6 caracteres", key="np1")
        nova2 = st.text_input("Confirmar nova senha:", type="password", placeholder="Repita a senha", key="np2")

        if st.button("✅ SALVAR NOVA SENHA", type="primary"):
            if not nova1 or not nova2:
                st.error("Preencha os dois campos.")
            elif len(nova1) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif nova1 != nova2:
                st.error("As senhas não coincidem.")
            else:
                novo_hash = gerar_hash_senha(nova1)
                if salvar_nova_senha(_reset_email, novo_hash):
                    st.success("✅ Senha redefinida com sucesso! Você já pode fazer login.")
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar. Tente novamente.")
    else:
        if st.button("⬅️ Voltar ao Login"):
            st.query_params.clear()
            st.rerun()

    st.stop()  # ← Impede o resto do app de renderizar

# --- FUNÇÕES DE SUPORTE ---

def disparar_email(destinatario, link):
    remetente = "tecpulverbrasil@gmail.com"
    try:
        senha_app = st.secrets["SMTP_PASSWORD"]
    except KeyError:
        try:
            senha_app = st.secrets["default"]["SMTP_PASSWORD"]
        except KeyError:
            senha_app = None

    if not senha_app:
        st.error("⚠️ Senha SMTP não encontrada.")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"TecPulver Brasil <{remetente}>"
    msg['To'] = destinatario
    msg['Subject'] = "🔐 Redefinir sua senha - TecPulver"

    corpo_html = f"""
    <html>
        <body style="font-family: sans-serif; background-color: #0a0f1e; padding: 30px; color: white;">
            <div style="max-width: 500px; margin: auto; background: #111827; padding: 30px; border-radius: 14px; border: 1px solid #2e7d32;">
                <h2 style="color: #4ade80; text-align: center;">🌿 TecPulver Brasil</h2>
                <p>Recebemos uma solicitação para redefinir sua senha de acesso ao sistema.</p>
                <p>Clique no botão abaixo para escolher uma nova senha:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{link}" style="background-color: #166534; color: white; padding: 14px 28px;
                       text-decoration: none; border-radius: 10px; font-weight: bold;
                       display: inline-block; border: 1px solid #4ade80;">
                        🔑 REDEFINIR MINHA SENHA
                    </a>
                </div>
                <p style="font-size: 0.8em; color: #6b7280; text-align: center;">
                    Este link é de uso único e expira após ser utilizado.
                </p>
            </div>
        </body>
    </html>
    """
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remetente, senha_app)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return False


def hash_senha(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()


def registrar_usuario_google_forms(nome, email, senha_hash):
    url = "https://docs.google.com/forms/d/e/1FAIpQLScZpMscEMElHo7Ya-i4DzrVnN7Au6NP0EXbi44eJ3_YzPxBpA/formResponse"
    dados = {
        "entry.7570846": nome,
        "entry.1437083228": email,
        "entry.519648678": senha_hash,
    }
    try:
        resposta = requests.post(url, data=dados, timeout=10)
        if resposta.ok:
            return True
        else:
            st.error(f"⚠️ Erro no servidor do Google: {resposta.status_code}")
            return False
    except Exception as e:
        st.error(f"❌ Falha na conexão com o banco de dados: {e}")
        return False


def email_existe(email):
    df = carregar_usuarios_planilha()
    if not df.empty and 'Email' in df.columns:
        lista_emails = df['Email'].astype(str).str.strip().str.lower().values
        return email.strip().lower() in lista_emails
    return False


def validar_login(email, senha):
    df = carregar_usuarios_planilha()
    if df is None or df.empty:
        return False
    email_norm = email.strip().lower()
    coluna_email = df['Email'].astype(str).str.strip().str.lower()
    linha = df[coluna_email == email_norm]
    if linha.empty:
        return False
    senha_hash_armazenada = linha.iloc[0]['SenhaHash']
    if pd.isna(senha_hash_armazenada) or str(senha_hash_armazenada).strip() == '':
        return True
    return hash_senha(senha) == str(senha_hash_armazenada).strip()


def gerar_token():
    return secrets.token_urlsafe(32)


@st.cache_data
def carregar_produtos_turbo(classe):
    mapa = {
        "Herbicidas": "herbicidas.csv",
        "Fungicidas": "fungicidas.csv",
        "Inseticidas": "inseticidas.csv",
        "Reguladores": "reguladores.csv",
    }
    
    arquivo = mapa.get(classe)
    
    if not arquivo:
        return ["Classe não encontrada"]

    try:
        # Pega o caminho da pasta onde o app.py está rodando
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_completo = os.path.join(diretorio_atual, arquivo)

        # Verifica se o arquivo realmente existe no GitHub/Pasta
        if os.path.exists(caminho_completo):
            # Lendo o CSV
            # Se o seu CSV usar ponto e vírgula (;), mude sep=',' para sep=';'
            df = pd.read_csv(caminho_completo, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
            
            # Pega a primeira coluna (geralmente o nome do produto), remove nulos e duplicados
            lista_produtos = df.iloc[:, 0].dropna().unique().tolist()
            return sorted(lista_produtos)
        else:
            return [f"Erro: Arquivo {arquivo} não encontrado no servidor."]

    except Exception as e:
        return [f"Erro ao ler o arquivo {arquivo}: {e}"]


# ============================================================
# PÁGINA 1 — LOGIN / CADASTRO / RECUPERAÇÃO DE SENHA
# ============================================================
def pagina_login():
    # --- LOGO ---
    html_logo = """
    <div style='display: flex; justify-content: center; align-items: center; margin-bottom: 25px;'>
        <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"
             style='filter: drop-shadow(0px 0px 10px rgba(255,255,255,0.3));'>
            <path d="M 20 80 A 30 30 0 0 1 80 80" stroke="white" stroke-width="6" stroke-linecap="round" fill="none"/>
            <line x1="50" y1="15" x2="50" y2="60" stroke="white" stroke-width="6" stroke-linecap="round"/>
            <path d="M 50 82 L 35 62 L 65 62 Z" fill="white"/>
        </svg>
    </div>
    """
    st.markdown(html_logo, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center; color: white; margin-bottom: 30px;'>TecPulver Brasil</h1>",
                unsafe_allow_html=True)

    # --- ABAS ---
    t1, t2, t3 = st.tabs(["🔐 Entrar", "📝 Criar Conta", "🔑 Recuperar"])

    # ── ABA 1: LOGIN ──
    with t1:
        campo_email = st.text_input("E-mail:", key="e_login_input", placeholder="seu@email.com")
        campo_senha = st.text_input("Senha:", type="password", key="s_login_input", placeholder="******")
        manter = st.checkbox("Manter-se conectado", value=True, key="check_manter")

        if st.button("ACESSAR PLATAFORMA", type="primary"):
            e_login = campo_email.strip().lower()
            s_login = campo_senha.strip()

            if not e_login or not s_login:
                st.error("⚠️ Preencha todos os campos.")
            else:
                with st.spinner("Validando acesso..."):
                    df_usuarios = carregar_usuarios_planilha()

                    if not df_usuarios.empty:
                        df_usuarios['Email'] = df_usuarios['Email'].astype(str).str.strip().str.lower()
                        usuario_validado = df_usuarios[df_usuarios['Email'] == e_login]

                        if not usuario_validado.empty:
                            senha_gravada = str(usuario_validado.iloc[0]['SenhaHash']).strip()
                            senha_digitada_hash = hash_senha(s_login)

                            if senha_digitada_hash == senha_gravada:
                                st.session_state.autenticado = True
                                st.session_state.usuario_logado = e_login
                                if st.session_state.get("check_manter"):
                                    st.query_params["u"] = e_login
                                st.success("✅ Acesso liberado!")
                                st.rerun()
                            else:
                                st.error("❌ Senha incorreta.")
                        else:
                            st.error(f"❌ O e-mail '{e_login}' não foi encontrado.")
                    else:
                        st.error("❌ Erro ao conectar com a base de dados. Tente novamente.")

    # ── ABA 2: CADASTRO ──
    with t2:
        st.subheader("📝 Criar Nova Conta")
        n_cad = st.text_input("Nome Completo", key="reg_nome_input")
        e_cad = st.text_input("E-mail", key="reg_email_input")
        s_cad = st.text_input("Senha", type="password", key="reg_senha_input")
        s_cad_conf = st.text_input("Confirme a Senha", type="password", key="reg_conf_input")

        if st.button("FINALIZAR CADASTRO", type="primary", key="btn_finalizar_registro"):
            if n_cad and e_cad and s_cad and s_cad_conf:
                nome_f = n_cad.strip()
                email_f = e_cad.strip().lower()
                senha_f = s_cad.strip()
                conf_f = s_cad_conf.strip()

                if len(senha_f) < 6:
                    st.error("⚠️ A senha deve ter no mínimo 6 caracteres.")
                elif senha_f != conf_f:
                    st.error("❌ As senhas não coincidem.")
                elif email_existe(email_f):
                    st.error("❌ Este e-mail já está cadastrado.")
                else:
                    with st.spinner("Gravando na nuvem..."):
                        sucesso = registrar_usuario_google_forms(nome_f, email_f, hash_senha(senha_f))
                        if sucesso:
                            st.session_state.autenticado = True
                            st.session_state.usuario_logado = email_f
                            st.success("✅ Conta criada com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar. Verifique sua conexão.")
            else:
                st.warning("⚠️ Por favor, preencha todos os campos acima.")

    # ── ABA 3: RECUPERAR SENHA ──
    with t3:
        st.subheader("🔑 Recuperar Acesso")
        st.write("Insira seu e-mail abaixo para receber o link de recuperação.")
        email_rec = st.text_input("E-mail de cadastro:", key="e_rec_input",
                                  placeholder="seu@email.com").strip().lower()

        if st.button("SOLICITAR RECUPERAÇÃO", type="primary", key="btn_recuperar"):
            if not email_rec:
                st.error("⚠️ Por favor, digite o seu e-mail.")
            else:
                with st.spinner("Conectando à base de dados..."):
                    try:
                        sheet = conectar_planilha()
                        cell = sheet.find(email_rec) # Localiza o e-mail
                        
                        token = gerar_token()
                        
                        # Grava na Coluna 6 (Coluna F - Token)
                        sheet.update_cell(cell.row, 6, token)

                        # Gera o link
                        url_app = "https://tecpulver-brasil.streamlit.app"
                        link_reset = f"{url_app}/?reset_token={token}&email={email_rec}"

                        if disparar_email(email_rec, link_reset):
                            st.success("✅ Link enviado! Verifique sua caixa de entrada.")
                    
                    except CellNotFound:
                        st.error("❌ E-mail não encontrado na base de dados.")
                    except Exception as e:
                        st.error(f"❌ Erro ao processar: {e}")
# ============================================================
# PÁGINA PRINCIPAL — SÓ EXECUTA SE ESTIVER LOGADO
# ============================================================
def pagina_principal():
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
    """
    st.markdown(html_cabecalho, unsafe_allow_html=True)

    col_user, col_btn_sair = st.columns([3, 1])
    with col_user:
        st.markdown(
            f"<p style='color:#aaaaaa !important; font-size: 0.85em; margin-left: 60px;'>"
            f"🛰️ Monitoramento Ativo: {st.session_state.usuario_logado}</p>",
            unsafe_allow_html=True
        )
    with col_btn_sair:
        if st.button("🚪 SAIR", key="sair_topo_final"):
            st.session_state.autenticado = False
            st.session_state.usuario_logado = None
            st.query_params.clear()
            st.rerun()

    st.divider()

    if st.session_state.get("usuario_logado") in ["fgustavo992@gmail.com", "felipe_fgd_@hotmail.com"]:
        st.warning("🛠️ GESTOR")
        st.link_button("📊 PLANILHA", "https://docs.google.com/spreadsheets/d/1-ra4aDcLc_UDokHszNUGXRRWNUE9hQfuwsD18HPAy0Y/")

    st.divider()

    # --- FORMULÁRIO TÉCNICO ---
    uf_sel = st.selectbox(
        "📍 ESTADO (UF):",
        options=["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
                 "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"],
        index=None,
        placeholder="Digite aqui..."
    )

    cidades = []
    if uf_sel:
        try:
            res = requests.get(
                f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sel}/municipios"
            )
            cidades = sorted([m['nome'] for m in res.json()]) if res.status_code == 200 else []
        except:
            cidades = []

    cid_sel = st.selectbox(
        "🏙️ CIDADE:",
        options=cidades,
        index=None,
        placeholder="Digite aqui...",
        disabled=not uf_sel
    )

    st.markdown("---")

    classe_sel = st.selectbox(
        "🧪 CLASSE QUÍMICA:",
        options=["Herbicidas","Fungicidas","Inseticidas","Reguladores"],
        index=None,
        placeholder="Digite aqui..."
    )
    opcoes_prod = carregar_produtos_turbo(classe_sel) if classe_sel else []
    prod_sel = st.selectbox(
        "📦 PRODUTO COMERCIAL:",
        options=opcoes_prod,
        index=None,
        placeholder="Digite aqui...",
        disabled=not classe_sel
    )
    tipo_app = st.radio("🚜 MODALIDADE:", ["Terrestre", "Aérea"], horizontal=True)

    st.divider()

    if st.button("VERIFICAR CONDIÇÕES AGORA", type="primary"):
        if uf_sel and cid_sel and prod_sel:
            try:
                cidade_url = cid_sel.replace(" ", "%20")
                geo_url = (
                    f"https://nominatim.openstreetmap.org/search"
                    f"?city={cidade_url}&state={uf_sel}&country=Brazil&format=json"
                )
                headers = {'User-Agent': 'TecPulver-App-Felipe'}
                geo_res = requests.get(geo_url, headers=headers).json()

                if geo_res:
                    lat, lon = geo_res[0]['lat'], geo_res[0]['lon']
                    clima_url = (
                        f"https://api.open-meteo.com/v1/forecast"
                        f"?latitude={lat}&longitude={lon}"
                        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
                        f"&forecast_days=2"
                    )
                    res_clima = requests.get(clima_url).json()

                    st.markdown(f"### 🛰️ Planejamento 24h: {cid_sel} - {uf_sel}")

                    dados_horas = res_clima['hourly']
                    hora_atual = datetime.now().hour
                    linhas_html = ""

                    for i in range(hora_atual, hora_atual + 24):
                        T  = dados_horas['temperature_2m'][i]
                        UR = dados_horas['relative_humidity_2m'][i]
                        V  = dados_horas['wind_speed_10m'][i]

                        tw = (T * math.atan(0.151977 * math.pow(UR + 8.313659, 0.5)) +
                              math.atan(T + UR) - math.atan(UR - 1.676331) +
                              0.00391838 * math.pow(UR, 1.5) * math.atan(0.023101 * UR) - 4.686035)
                        dt_real = round(T - tw, 1)

                        ideal  = (10.0 <= T <= 30.0) and (2.0 <= dt_real <= 8.0) and (2.0 <= V <= 12.0)
                        cor_dt = "#4ade80" if 2.0 <= dt_real <= 8.0 else "#f87171"
                        row_bg     = "rgba(74,222,128,0.06)"   if ideal else "rgba(255,255,255,0.02)"
                        row_border = "1px solid rgba(74,222,128,0.15)" if ideal else "1px solid rgba(255,255,255,0.05)"

                        if ideal:
                            badge = """
                            <span style="display:inline-flex; align-items:center; gap:5px;
                                background: linear-gradient(135deg, #14532d, #166534);
                                color: #bbf7d0; padding: 5px 14px; border-radius: 999px;
                                font-size: 0.75em; font-weight: 700; letter-spacing: 0.05em;
                                border: 1px solid rgba(74,222,128,0.3); text-transform: uppercase;">
                                ✅ IDEAL</span>"""
                        else:
                            badge = """
                            <span style="display:inline-flex; align-items:center; gap:5px;
                                background: linear-gradient(135deg, #450a0a, #7f1d1d);
                                color: #fca5a5; padding: 5px 14px; border-radius: 999px;
                                font-size: 0.75em; font-weight: 700; letter-spacing: 0.05em;
                                border: 1px solid rgba(248,113,113,0.3); text-transform: uppercase;">
                                ❌ INADEQUADO</span>"""

                        linhas_html += f"""
                        <tr style="background:{row_bg}; border-bottom:{row_border}; transition: background 0.2s;">
                            <td style="padding:13px 16px; text-align:center;">
                                <span style="background: rgba(165,214,167,0.12); color: #a5d6a7;
                                    font-family: 'Courier New', monospace; font-weight: 800;
                                    font-size: 0.95em; padding: 4px 10px; border-radius: 6px;
                                    border: 1px solid rgba(165,214,167,0.2); letter-spacing: 0.05em;">
                                    {i % 24:02d}:00</span>
                            </td>
                            <td style="padding:13px 16px; text-align:center; color:#e2e8f0; font-size:0.95em; font-weight:600;">
                                {T:.1f}<span style="color:#94a3b8; font-size:0.8em; margin-left:2px;">°C</span>
                            </td>
                            <td style="padding:13px 16px; text-align:center; color:{cor_dt}; font-weight:900; font-size:1.05em; letter-spacing:0.02em;">
                                {dt_real}
                            </td>
                            <td style="padding:13px 16px; text-align:center; color:#e2e8f0; font-size:0.95em; font-weight:600;">
                                {UR:.0f}<span style="color:#94a3b8; font-size:0.8em; margin-left:2px;">%</span>
                            </td>
                            <td style="padding:13px 16px; text-align:center; color:#e2e8f0; font-size:0.95em; font-weight:600;">
                                {V:.1f}<span style="color:#94a3b8; font-size:0.8em; margin-left:2px;">km/h</span>
                            </td>
                            <td style="padding:13px 16px; text-align:center;">{badge}</td>
                        </tr>
                        """

                    tabela_completa = f"""
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600;700&display=swap');
                        .tp-table-wrapper {{
                            font-family: 'IBM Plex Sans', sans-serif;
                            background: #0a0f1e; border-radius: 14px; overflow: hidden;
                            border: 1px solid rgba(255,255,255,0.08);
                            box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(74,222,128,0.05);
                        }}
                        .tp-table-wrapper table {{ width: 100%; border-collapse: collapse; }}
                        .tp-table-wrapper thead tr {{
                            background: linear-gradient(90deg, #0d1f12, #0a1a2e);
                            border-bottom: 2px solid rgba(74,222,128,0.25);
                        }}
                        .tp-table-wrapper thead th {{
                            padding: 14px 16px; text-align: center; font-size: 0.7em;
                            font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #6b7280;
                        }}
                        .tp-table-wrapper thead th.col-dt {{ color: #4ade80; }}
                        .tp-table-wrapper tbody tr:hover {{ background: rgba(255,255,255,0.04) !important; }}
                        .tp-table-wrapper tbody tr:last-child {{ border-bottom: none !important; }}
                    </style>
                    <div class="tp-table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>🕐 Hora</th>
                                    <th>🌡️ Temp</th>
                                    <th class="col-dt">⬦ Delta T</th>
                                    <th>💧 Umid</th>
                                    <th>💨 Vento</th>
                                    <th>● Status</th>
                                </tr>
                            </thead>
                            <tbody>{linhas_html}</tbody>
                        </table>
                    </div>
                    """
                    components.html(tabela_completa, height=900, scrolling=True)
                else:
                    st.error("Cidade não localizada.")
            except Exception as e:
                st.error(f"Erro no cálculo: {e}")
        else:
            st.warning("⚠️ Selecione Estado, Cidade e Produto antes de verificar.")

    if st.session_state.get("usuario_logado") in ["fgustavo992@gmail.com", "felipe_fgd_@hotmail.com"]:
        st.markdown("---")
        st.warning("🛠️ PAINEL DE CONTROLE DO GESTOR")
        st.write("A base de dados agora é gerenciada via Google Sheets para maior segurança.")
        st.link_button(
            "📊 ACESSAR BASE DE DADOS (GOOGLE SHEETS)",
            "https://docs.google.com/spreadsheets/d/1-ra4aDcLc_UDokHszNUGXRRWNUE9hQfuwsD18HPAy0Y/",
            use_container_width=True
        )
        st.info("Dica: Os novos cadastros feitos via Instagram aparecerão na planilha em tempo real.")


# ============================================================
# ROTEADOR
# ============================================================
params = st.query_params

if not st.session_state.get("autenticado", False) and params.get("u"):
    st.session_state.autenticado = True
    st.session_state.usuario_logado = params["u"]

if st.session_state.get("autenticado", False):
    pagina_principal()
else:
    pagina_login()
