import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
from datetime import datetime
import os
import math
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. CONFIGURAÇÃO E IDENTIDADE VISUAL ---
st.set_page_config(page_title="TecPulver Brasil", layout="centered", page_icon="🟢")

# INJEÇÃO OCULTA DE METADADOS PWA (CORRIGIDO)
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
    background: #2e7d32; 
    padding: 12px;
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
    div[data-testid="stButton"].sair-btn > button {
        background-color: #c0392b !important;
    }
    .stSelectbox label, .stRadio label, p, h3, h4, span, h1, h2 { color: #ffffff !important; font-weight: 600 !important; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE ---

def hash_senha(senha):
    """Gera hash SHA-256 da senha."""
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def registrar_usuario_google_forms(nome, email, senha_hash):
    # Link direto para o processamento do formulário
    url = "https://docs.google.com/forms/d/e/1FAIpQLScZpMscEMElHo7Ya-i4DzrVnN7Au6NP0EXbi44eJ3_YzPxBpA/formResponse"
    
    # Códigos extraídos do seu formulário original
    dados = {
        "entry.2045580665": nome,        # Campo Nome
        "entry.1983084776": email,       # Campo Email
        "entry.1492212937": senha_hash,  # Campo SenhaHash
        "entry.1610425488": datetime.now().strftime("%d/%m/%Y %H:%M") # Campo Data
    }
    
    try:
        import requests
        # Envia os dados para a planilha de forma silenciosa
        requests.post(url, data=dados)
        return True
    except:
        return False
def carregar_usuarios_planilha():
    # Este é o seu link de publicação ajustado para leitura de dados
    url_csv = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS6P99XsCL2-uu9QqDSCwWmgYyyk3h6cfoLw27FFvwMytxEyDT7EfMBOFVs5tyYj1kIuZyruXjU0_7h/pub?output=csv"
    
    try:
        # Lê os dados da planilha em tempo real sem precisar de senhas complexas
        df = pd.read_csv(url_csv)
        # Remove espaços em branco dos nomes das colunas para evitar erros
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        # Se der erro (ex: planilha sem dados ainda), retorna um DataFrame vazio
        return pd.DataFrame()
def email_existe(email):
    df = carregar_usuarios_planilha()
    if not df.empty and 'Email' in df.columns:
        # O segredo é o .astype(str), que converte qualquer erro ou vazio em texto
        lista_emails = df['Email'].astype(str).str.strip().str.lower().values
        return email.strip().lower() in lista_emails
    return False

def validar_login(email, senha):
    """Valida email e senha. Retorna True se correto."""
    df = carregar_usuarios_planilha()
    if df is None:
        return False
    email_norm = email.strip().lower()
    linha = df[df['Email'].str.strip().str.lower() == email_norm]
    if linha.empty:
        return False
    senha_hash_armazenada = linha.iloc[0]['SenhaHash']
    # Compatibilidade: se não há hash salvo (usuário antigo), aceita qualquer senha
    if pd.isna(senha_hash_armazenada) or str(senha_hash_armazenada).strip() == '':
        return True
    return hash_senha(senha) == str(senha_hash_armazenada).strip()

def salvar_nova_senha(email, nova_senha_hash):
    """Atualiza a senha de um usuário no CSV."""
    arquivo = 'usuarios_cadastrados.csv'
    df = carregar_usuarios_planilha()
    if df is None:
        return False
    email_norm = email.strip().lower()
    mask = df['Email'].str.strip().str.lower() == email_norm
    if not mask.any():
        return False
    df.loc[mask, 'SenhaHash'] = nova_senha_hash
    df.to_csv(arquivo, index=False, sep=';', encoding='utf-8-sig')
    return True

def gerar_token():
    """Gera token seguro de redefinição de senha."""
    return secrets.token_urlsafe(32)

def enviar_email_redefinicao(email_destino, token):
    """Envia email de redefinição de senha via Gmail SMTP."""
    try:
        gmail_user = st.secrets["gmail"]["usuario"]
        gmail_pass = st.secrets["gmail"]["senha_app"]
    except Exception:
        return False, "Credenciais de email não configuradas nos Secrets do Streamlit."

    link = f"https://tecpulver-brasil.streamlit.app/?reset_token={token}&email={email_destino}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🔐 TecPulver Brasil — Redefinição de Senha"
    msg["From"] = gmail_user
    msg["To"] = email_destino

    corpo_html = f"""
    <html>
    <body style="background:#0a0f1e; font-family: sans-serif; padding: 30px;">
        <div style="max-width:480px; margin:auto; background:#111827; border-radius:14px;
                    border:1px solid rgba(74,222,128,0.2); padding:30px;">
            <h2 style="color:#4ade80; margin-top:0;">🌿 TecPulver Brasil</h2>
            <p style="color:#e2e8f0;">Recebemos uma solicitação para redefinir a senha da sua conta.</p>
            <p style="color:#e2e8f0;">Clique no botão abaixo para criar uma nova senha:</p>
            <a href="{link}" style="
                display:inline-block; margin:20px 0;
                background:linear-gradient(135deg,#14532d,#166534);
                color:#bbf7d0; padding:14px 28px; border-radius:10px;
                text-decoration:none; font-weight:700; font-size:1em;
                border:1px solid rgba(74,222,128,0.3);">
                🔑 Redefinir Minha Senha
            </a>
            <p style="color:#6b7280; font-size:0.8em;">
                Este link expira em 1 hora. Se você não solicitou a redefinição, ignore este email.
            </p>
            <hr style="border-color:rgba(255,255,255,0.08); margin-top:20px;">
            <p style="color:#374151; font-size:0.75em;">TecPulver Brasil — Monitoramento Agronômico</p>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(corpo_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, email_destino, msg.as_string())
        return True, "ok"
    except Exception as e:
        return False, str(e)

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

# --- 3. FLUXO DE REDEFINIÇÃO DE SENHA VIA TOKEN NA URL ---
params = st.query_params

# Armazena tokens de redefinição na sessão: {token: email}
if 'reset_tokens' not in st.session_state:
    st.session_state.reset_tokens = {}

reset_token_url = params.get("reset_token", "")
reset_email_url = params.get("email", "")

if reset_token_url and reset_email_url:
    token_valido = st.session_state.reset_tokens.get(reset_token_url) == reset_email_url.strip().lower()

    st.markdown("<h2 style='text-align:center; color:white;'>🔑 Redefinir Senha</h2>", unsafe_allow_html=True)

    if not token_valido:
        st.error("❌ Link inválido ou expirado. Solicite um novo link na tela de login.")
        if st.button("⬅️ Voltar ao Login"):
            st.query_params.clear()
            st.rerun()
    else:
        nova1 = st.text_input("Nova senha:", type="password", placeholder="Mínimo 6 caracteres")
        nova2 = st.text_input("Confirmar nova senha:", type="password", placeholder="Repita a senha")
        if st.button("✅ SALVAR NOVA SENHA", type="primary"):
            if not nova1 or not nova2:
                st.error("Preencha os dois campos.")
            elif len(nova1) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif nova1 != nova2:
                st.error("As senhas não coincidem.")
            else:
                ok = salvar_nova_senha(reset_email_url, hash_senha(nova1))
                if ok:
                    del st.session_state.reset_tokens[reset_token_url]
                    st.success("✅ Senha redefinida com sucesso! Faça login agora.")
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("Erro ao salvar senha. Verifique se o email está cadastrado.")
    st.stop()

# --- 4. SISTEMA DE ACESSO COM PERSISTÊNCIA, SENHA E RECUPERAÇÃO ---
if 'autenticado' not in st.session_state:
    if params.get("u"):
        st.session_state.autenticado = True
        st.session_state.usuario_logado = params["u"]
    else:
        st.session_state.autenticado = False

if not st.session_state.autenticado:
    # Renderização do Logo (Mantendo seu estilo)
    html_simbolo_grande = """
    <div style='display: flex; justify-content: center; align-items: center; margin-bottom: 25px;'>
        <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style='filter: drop-shadow(0px 0px 10px rgba(255,255,255,0.3));'>
            <path d="M 20 80 A 30 30 0 0 1 80 80" stroke="white" stroke-width="6" stroke-linecap="round" fill="none"/>
            <line x1="50" y1="15" x2="50" y2="60" stroke="white" stroke-width="6" stroke-linecap="round"/>
            <path d="M 50 82 L 35 62 L 65 62 Z" fill="white"/>
        </svg>
    </div>
    """
    st.markdown(html_simbolo_grande, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center; color: white; margin-bottom: 30px;'>TecPulver Brasil</h1>", unsafe_allow_html=True)

    # Criação das 3 abas solicitadas
    t1, t2, t3 = st.tabs(["🔐 Entrar", "📝 Criar Conta", "🔑 Recuperar"])

    with t1: # Aba de Login
        e_login = st.text_input("E-mail:", key="e_login_input", placeholder="seu@email.com").strip().lower()
        s_login = st.text_input("Senha:", type="password", key="s_login_input", placeholder="******")
        manter = st.checkbox("Manter-se conectado", value=True, key="check_manter")

        if st.button("ACESSAR PLATAFORMA", type="primary"):
            if not e_login or not s_login:
                st.error("⚠️ Preencha todos os campos.")
            else:
                # Carrega da planilha (URL que termina em pub?output=csv)
                df_usuarios = carregar_usuarios_planilha()
                
                if not df_usuarios.empty:
                    # O SEGREDO ESTÁ AQUI: .astype(str) evita o erro que você teve
                    try:
                        # Filtra a planilha procurando o e-mail
                        coluna_email = df_usuarios['Email'].astype(str).str.strip().str.lower()
                        usuario_validado = df_usuarios[coluna_email == e_login]
                        
                        if not usuario_validado.empty:
                            senha_gravada = str(usuario_validado.iloc[0]['SenhaHash']).strip()
                            
                            if hash_senha(s_login) == senha_gravada:
                                st.session_state.autenticado = True
                                st.session_state.usuario_logado = e_login
                                if manter:
                                    st.query_params["u"] = e_login
                                st.success("✅ Acesso liberado!")
                                st.rerun()
                            else:
                                st.error("❌ Senha incorreta.")
                        else:
                            st.error("❌ Usuário não encontrado.")
                    except Exception as e:
                        st.error(f"❌ Erro na estrutura da planilha: {e}")
                else:
                    st.error("❌ Base de dados vazia ou inacessível.")
        # Esta é a aba de Cadastro
    with t2: # Aba de Cadastro
        # Verifique se os nomes antes do '=' batem com os nomes no 'if' abaixo
        n_cad = st.text_input("Nome Completo", key="cad_nome")
        e_cad = st.text_input("E-mail", key="cad_email").strip().lower()
        s_cad = st.text_input("Senha", type="password", key="cad_senha")
        s_cad_conf = st.text_input("Confirme a Senha", type="password", key="cad_conf_senha")

    if st.button("FINALIZAR CADASTRO", type="secondary"):
        # Aqui é onde o erro acontece se as variáveis acima tiverem nomes diferentes
        if not n_cad or not e_cad or not s_cad or not s_cad_conf:
            st.error("⚠️ Por favor, preencha todos os campos.")
        elif len(s_cad) < 6:
            st.error("⚠️ A senha deve ter no mínimo 6 caracteres.")
        # ... resto do código
        elif s_cad != s_cad_conf:
                st.error("❌ As senhas não coincidem.")
                 # Nota: A função email_existe ainda lerá o CSV antigo se não for atualizada
        elif email_existe(e_cad):
                st.error("❌ Este e-mail já está cadastrado.")
        else:
                # Chamada para a função que configuramos com os IDs do seu formulário
                sucesso = registrar_usuario_google_forms(n_cad, e_cad, hash_senha(s_cad))
                
                if sucesso:
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = e_cad
                    st.query_params["u"] = e_cad
                    st.success("✅ Conta criada com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar cadastro na nuvem. Verifique sua conexão.")
    with t3: # Aba de Recuperar
        st.subheader("🔑 Recuperar Acesso")
        st.write("Insira seu e-mail abaixo para validar sua conta.")
        
        email_rec = st.text_input("E-mail de cadastro:", key="e_rec_input", placeholder="seu@email.com").strip().lower()

        # AQUI VOCÊ MUDA O NOME DO BOTÃO:
        if st.button("SOLICITAR RECUPERAÇÃO", type="primary", key="btn_recuperar_aba"):
            if not email_rec:
                st.error("⚠️ Por favor, digite o seu e-mail.")
            else:
                # Verifica na planilha se o e-mail existe
                if email_existe(email_rec):
                    st.success(f"✅ O e-mail {email_rec} foi localizado em nossa base!")
                    st.info("⚠️ Como este é um app de demonstração, entre em contato com o suporte para redefinir sua senha manualmente.")
                else:
                    st.error("❌ Este e-mail não consta em nossa base de produtores.")

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.usuario_logado}**")
    st.divider()
with st.sidebar:
    st.markdown("### 📱 Instalar no Celular")
    if st.checkbox("Como instalar?"):
        st.info("""
        **No Android (Chrome):**
        1. Clique nos 3 pontinhos (⋮) no topo.
        2. Clique em **'Instalar aplicativo'**.
        
        **No iOS (Safari):**
        1. Clique no botão de **Compartilhar** (quadrado com seta).
        2. Role para baixo e clique em **'Adicionar à Tela de Início'**.
        """)
    st.divider()
    if st.button("🚪 SAIR DA CONTA", key="sair_sidebar"):
        st.session_state.autenticado = False
        st.query_params.clear()
        st.rerun()

# --- 6. MODO GESTOR (REFORMULADO PARA GOOGLE SHEETS) ---
if st.session_state.usuario_logado in ["fgustavo992@gmail.com", "felipe_fgd_@hotmail.com"]:
    st.markdown("---")
    st.warning("🛠️ PAINEL DE CONTROLE DO GESTOR")
    
    st.write("A base de dados agora é gerenciada via Google Sheets para maior segurança.")
    
    # Botão direto para a sua planilha
    st.link_button(
        "📊 ACESSAR BASE DE DADOS (GOOGLE SHEETS)", 
        "https://docs.google.com/spreadsheets/d/1-ra4aDcLc_UDokHszNUGXRRWNUE9hQfuwsD18HPAy0Y/",
        use_container_width=True
    )
    
    st.info("Dica: Os novos cadastros feitos via Instagram aparecerão na planilha em tempo real.")
# --- 7. CABEÇALHO ---
header_container = st.container()

with header_container:
    col_titulo, col_sair = st.columns([4, 1])
    
    with col_titulo:
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

# --- 8. FORMULÁRIO TÉCNICO ---
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

# --- 9. EXECUÇÃO DA ANÁLISE ---
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
                
                dados_horas = res_clima['hourly']
                hora_atual = datetime.now().hour
                linhas_html = ""

                for i in range(hora_atual, hora_atual + 24):
                    T = dados_horas['temperature_2m'][i]
                    UR = dados_horas['relative_humidity_2m'][i]
                    V = dados_horas['wind_speed_10m'][i]

                    # --- FÓRMULA DE STULL ---
                    tw = (T * math.atan(0.151977 * math.pow(UR + 8.313659, 0.5)) +
                          math.atan(T + UR) - math.atan(UR - 1.676331) +
                          0.00391838 * math.pow(UR, 1.5) * math.atan(0.023101 * UR) - 4.686035)
                    dt_real = round(T - tw, 1)

                    ideal = (10.0 <= T <= 30.0) and (2.0 <= dt_real <= 8.0) and (2.0 <= V <= 12.0)

                    cor_dt = "#4ade80" if 2.0 <= dt_real <= 8.0 else "#f87171"

                    row_bg = "rgba(74,222,128,0.06)" if ideal else "rgba(255,255,255,0.02)"
                    row_border = "1px solid rgba(74,222,128,0.15)" if ideal else "1px solid rgba(255,255,255,0.05)"

                    if ideal:
                        badge = """
                        <span style="
                            display:inline-flex; align-items:center; gap:5px;
                            background: linear-gradient(135deg, #14532d, #166534);
                            color: #bbf7d0;
                            padding: 5px 14px;
                            border-radius: 999px;
                            font-size: 0.75em;
                            font-weight: 700;
                            letter-spacing: 0.05em;
                            border: 1px solid rgba(74,222,128,0.3);
                            text-transform: uppercase;
                        ">✅ IDEAL</span>"""
                    else:
                        badge = """
                        <span style="
                            display:inline-flex; align-items:center; gap:5px;
                            background: linear-gradient(135deg, #450a0a, #7f1d1d);
                            color: #fca5a5;
                            padding: 5px 14px;
                            border-radius: 999px;
                            font-size: 0.75em;
                            font-weight: 700;
                            letter-spacing: 0.05em;
                            border: 1px solid rgba(248,113,113,0.3);
                            text-transform: uppercase;
                        ">❌ INADEQUADO</span>"""

                    linhas_html += f"""
                    <tr style="background:{row_bg}; border-bottom:{row_border}; transition: background 0.2s;">
                        <td style="padding:13px 16px; text-align:center;">
                            <span style="
                                background: rgba(165,214,167,0.12);
                                color: #a5d6a7;
                                font-family: 'Courier New', monospace;
                                font-weight: 800;
                                font-size: 0.95em;
                                padding: 4px 10px;
                                border-radius: 6px;
                                border: 1px solid rgba(165,214,167,0.2);
                                letter-spacing: 0.05em;
                            ">{i % 24:02d}:00</span>
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
                        <td style="padding:13px 16px; text-align:center;">
                            {badge}
                        </td>
                    </tr>
                    """

                tabela_completa = f"""
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600;700&display=swap');

                    .tp-table-wrapper {{
                        font-family: 'IBM Plex Sans', sans-serif;
                        background: #0a0f1e;
                        border-radius: 14px;
                        overflow: hidden;
                        border: 1px solid rgba(255,255,255,0.08);
                        box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(74,222,128,0.05);
                    }}

                    .tp-table-wrapper table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}

                    .tp-table-wrapper thead tr {{
                        background: linear-gradient(90deg, #0d1f12, #0a1a2e);
                        border-bottom: 2px solid rgba(74,222,128,0.25);
                    }}

                    .tp-table-wrapper thead th {{
                        padding: 14px 16px;
                        text-align: center;
                        font-size: 0.7em;
                        font-weight: 700;
                        letter-spacing: 0.12em;
                        text-transform: uppercase;
                        color: #6b7280;
                    }}

                    .tp-table-wrapper thead th.col-dt {{
                        color: #4ade80;
                    }}

                    .tp-table-wrapper tbody tr:hover {{
                        background: rgba(255,255,255,0.04) !important;
                    }}

                    .tp-table-wrapper tbody tr:last-child {{
                        border-bottom: none !important;
                    }}
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
                        <tbody>
                            {linhas_html}
                        </tbody>
                    </table>
                </div>
                """

                components.html(tabela_completa, height=900, scrolling=True)

            else:
                st.error("Cidade não localizada.")
        except Exception as e:
            st.error(f"Erro no cálculo: {e}")
