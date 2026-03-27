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

# --- INICIALIZAÇÃO DO ESTADO DO SISTEMA ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

# --- 1. CONFIGURAÇÃO E IDENTIDADE VISUAL ---
st.set_page_config(page_title="TecPulver Brasil", layout="centered", page_icon="🟢")

# (Seu CSS e Meta de PWA permanecem iguais...)
st.markdown("""
    <style>
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
    .stSelectbox label, .stRadio label, p, h3, h4, span, h1, h2 { color: #ffffff !important; font-weight: 600 !important; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE (MANTIDAS COMO ESTÃO) ---
def hash_senha(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def carregar_usuarios_planilha():
    url_csv = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS6P99XsCL2-uu9QqDSCwWmgYyyk3h6cfoLw27FFvwMytxEyDT7EfMBOFVs5tyYj1kIuZyruXjU0_7h/pub?output=csv"
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

def email_existe(email):
    df = carregar_usuarios_planilha()
    if not df.empty and 'Email' in df.columns:
        lista_emails = df['Email'].astype(str).str.strip().str.lower().values
        return email.strip().lower() in lista_emails
    return False

def registrar_usuario_google_forms(nome, email, senha_hash):
    url = "https://docs.google.com/forms/d/e/1FAIpQLScZpMscEMElHo7Ya-i4DzrVnN7Au6NP0EXbi44eJ3_YzPxBpA/formResponse"
    dados = {
        "entry.2045580665": nome,
        "entry.1983084776": email,
        "entry.1492212937": senha_hash,
        "entry.1610425488": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    try:
        requests.post(url, data=dados)
        return True
    except:
        return False

@st.cache_data
def carregar_produtos_turbo(classe):
    mapa = {"Herbicidas": "herbicidas.csv", "Fungicidas": "fungicidas.csv", "Inseticidas": "inseticidas.csv", "Reguladores": "reguladores.csv"}
    arquivo = mapa.get(classe)
    if arquivo and os.path.exists(arquivo):
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
            return sorted(df.iloc[:, 0].dropna().unique().tolist())
        except: return [f"Erro na leitura"]
    return [f"Arquivo não encontrado"]

# --- 4. SISTEMA DE ACESSO ---
params = st.query_params
if not st.session_state.autenticado:
    if params.get("u"):
        st.session_state.autenticado = True
        st.session_state.usuario_logado = params["u"]
        st.rerun()

if not st.session_state.autenticado:
    # MOSTRA APENAS LOGIN SE NÃO AUTENTICADO
    st.markdown("<h1 style='text-align:center; color: white;'>TecPulver Brasil</h1>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🔐 Entrar", "📝 Criar Conta", "🔑 Recuperar"])

    with t1:
        e_login = st.text_input("E-mail:", key="e_login_input").strip().lower()
        s_login = st.text_input("Senha:", type="password", key="s_login_input")
        if st.button("ACESSAR PLATAFORMA", type="primary"):
            df_usuarios = carregar_usuarios_planilha()
            if not df_usuarios.empty:
                col_email = df_usuarios['Email'].astype(str).str.strip().str.lower()
                usuario_validado = df_usuarios[col_email == e_login]
                if not usuario_validado.empty:
                    if hash_senha(s_login) == str(usuario_validado.iloc[0]['SenhaHash']).strip():
                        st.session_state.autenticado = True
                        st.session_state.usuario_logado = e_login
                        st.query_params["u"] = e_login
                        st.rerun()
                    else: st.error("❌ Senha incorreta.")
                else: st.error("❌ Usuário não encontrado.")

    with t2:
        n_cad = st.text_input("Nome Completo", key="cad_nome")
        e_cad = st.text_input("E-mail", key="cad_email").strip().lower()
        s_cad = st.text_input("Senha", type="password", key="cad_senha")
        s_cad_conf = st.text_input("Confirme a Senha", type="password", key="cad_conf_senha")
        if st.button("FINALIZAR CADASTRO", type="primary", key="btn_cad_real"):
            if not n_cad or not e_cad or s_cad != s_cad_conf:
                st.error("⚠️ Verifique os campos.")
            elif email_existe(e_cad):
                st.error("❌ E-mail já cadastrado.")
            else:
                if registrar_usuario_google_forms(n_cad, e_cad, hash_senha(s_cad)):
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = e_cad
                    st.rerun()

    with t3:
        st.subheader("🔑 Recuperar Acesso")
        email_rec = st.text_input("E-mail de cadastro:", key="e_rec_input_final")
        # CORREÇÃO AQUI: Botão agora correto para recuperação
        if st.button("RECUPERAR SENHA", type="primary", key="btn_recuperar_final"):
            if email_existe(email_rec):
                st.success("✅ Conta localizada! Solicite o reset ao suporte.")
            else:
                st.error("❌ E-mail não encontrado.")

else:
    # --- CONTEÚDO DO APP (SÓ APARECE SE LOGADO) ---
    with st.sidebar:
        st.write(f"👤 **{st.session_state.usuario_logado}**")
        if st.button("🚪 Sair", key="sair_sidebar"):
            st.session_state.autenticado = False
            st.query_params.clear()
            st.rerun()

    # MODO GESTOR
    if st.session_state.usuario_logado in ["fgustavo992@gmail.com", "felipe_fgd_@hotmail.com"]:
        st.warning("🛠️ PAINEL DO GESTOR")
        st.link_button("📊 BASE DE DADOS", "https://docs.google.com/spreadsheets/d/1-ra4aDcLc_UDokHszNUGXRRWNUE9hQfuwsD18HPAy0Y/")

    # CABEÇALHO DO APP
    st.title("TecPulver Brasil")
    st.write(f"🛰️ Monitoramento Ativo: {st.session_state.usuario_logado}")
    st.divider()

    # FORMULÁRIO TÉCNICO (IBGE, PRODUTOS, DELTA T)
    uf_sel = st.selectbox("📍 ESTADO (UF):", options=["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"], index=None)
    
    cidades = []
    if uf_sel:
        res = requests.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sel}/municipios")
        cidades = sorted([m['nome'] for m in res.json()]) if res.status_code == 200 else []

    cid_sel = st.selectbox("🏙️ CIDADE:", options=cidades, index=None, disabled=not uf_sel)
    classe_sel = st.selectbox("🧪 CLASSE QUÍMICA:", options=["Herbicidas","Fungicidas","Inseticidas","Reguladores"], index=None)
    opcoes_prod = carregar_produtos_turbo(classe_sel) if classe_sel else []
    prod_sel = st.selectbox("📦 PRODUTO COMERCIAL:", options=opcoes_prod, index=None, disabled=not classe_sel)
    tipo_app = st.radio("🚜 MODALIDADE:", ["Terrestre", "Aérea"], horizontal=True)

    if st.button("VERIFICAR CONDIÇÕES AGORA", type="primary"):
        if uf_sel and cid_sel and prod_sel:
            # (Aqui continua toda a sua lógica de Delta T e Tabela HTML que você já tem...)
            st.info("Buscando dados climáticos...")
            # Copie aqui o restante do seu código do cálculo do Delta T e tabela HTML
