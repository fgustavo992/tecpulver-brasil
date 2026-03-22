import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import json
import urllib.parse

# --- 1. CONFIGURAÇÃO E IDENTIDADE VISUAL (FAVICON ATUALIZADO) ---
st.set_page_config(
    page_title="TecPulver Brasil", 
    layout="wide", 
    page_icon="🟢" # Ícone verde para a aba do navegador
)

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.88), rgba(0, 0, 0, 0.88)), 
                    url('https://images.unsplash.com/photo-1560493676-04071c5f467b?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80');
        background-size: cover; background-attachment: fixed;
    }
    .block-container { max-width: 800px !important; margin: auto; padding-top: 1.5rem; }
    
    /* ÍCONE E BOTÕES PROFISSIONAIS */
    .icon-sprayer {
        background: #2e7d32; padding: 20px; border-radius: 50%; display: inline-block;
        margin-bottom: 20px; box-shadow: 0 0 25px rgba(46, 125, 50, 0.6);
        border: 2px solid rgba(255,255,255,0.2);
    }
    
    /* DESTAQUE DOS BENEFÍCIOS (MAIS CLARO E VIBRANTE) */
    .beneficios-box {
        background: rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #4CAF50;
    }
    .beneficio-item {
        color: #ccff90 !important; /* Verde limão vibrante para leitura clara */
        font-weight: 800 !important;
        font-size: 1.1rem;
        margin-bottom: 8px;
    }
    .dados-precisos {
        color: #81c784;
        font-size: 0.9rem;
        font-style: italic;
        text-align: center;
        margin-top: 10px;
    }

    div.stButton > button {
        background-color: #4CAF50 !important; color: white !important;
        font-weight: 800 !important; font-size: 1.2rem !important;
        border-radius: 10px !important; border: none !important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4) !important;
        padding: 10px 20px !important; transition: all 0.3s ease !important;
    }
    
    /* STATUS E TABELA */
    .status-ideal { color: #00ff00 !important; font-weight: bold; background: rgba(0,255,0,0.1); padding: 5px 10px; border-radius: 5px; border: 1px solid #00ff00; }
    .status-critico { color: #ff4b4b !important; font-weight: bold; background: rgba(255,75,75,0.1); padding: 5px 10px; border-radius: 5px; border: 1px solid #ff4b4b; }
    .suporte-link { color: #81c784 !important; font-size: 0.85rem; text-decoration: none; display: block; margin-top: 20px; font-weight: bold; text-align: center; }
    
    .stSelectbox label, .stRadio label, p, h3, h4, span, h1, h2 { color: #ffffff !important; font-weight: 600 !important; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE E LOGO ---
def exibir_logo_padrao():
    st.markdown("""
        <div style='text-align: center;'>
            <div class='icon-sprayer'>
                <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5">
                    <path d="M12 2v10M8.5 8.5L12 12l3.5-3.5"></path>
                    <path d="M12 12c-3.3 0-6 2.7-6 6"></path>
                    <path d="M12 12c3.3 0 6 2.7 6 6"></path>
                    <circle cx="12" cy="18" r="1"></circle>
                </svg>
            </div>
        </div>
    """, unsafe_allow_html=True)

def exibir_link_erro():
    st.markdown("""<a href="https://docs.google.com/forms/d/e/1FAIpQLSdbXN5uS9uS3m-U_S9-GjR5LpC_V_B08CqY6g" target="_blank" class="suporte-link">⚠️ Relatar erro ou falha técnica</a>""", unsafe_allow_html=True)

# --- 3. MOTOR DE DADOS TURBO ---
@st.cache_resource
def carregar_produtos_turbo(classe):
    mapa = {
        "Herbicidas": "herbicidas.csv", "Fungicidas": "fungicidas.csv",
        "Inseticidas": "inseticidas.csv", "Reguladores": "reguladores.csv",
        "Adjuvantes/Outros": "adjuvantes.csv"
    }
    arquivo = mapa.get(classe)
    if os.path.exists(arquivo):
        try:
            df = pd.read_csv(arquivo)
            return df.iloc[:, 0].tolist()
        except: return []
    return []

def buscar_clima_24h(cidade, uf):
    try:
        geo = requests.get(f"https://nominatim.openstreetmap.org/search?city={cidade}&state={uf}&country=Brazil&format=json", headers={'User-Agent': 'TecPulver'}).json()
        lat, lon = geo[0]['lat'], geo[0]['lon']
        res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation_probability,precipitation&forecast_days=2").json()
        dados = res['hourly']
        agora = datetime.now().replace(minute=0, second=0, microsecond=0)
        lista = []
        for i in range(len(dados['time'])):
            dt_p = datetime.fromisoformat(dados['time'][i])
            if dt_p >= agora and len(lista) < 24:
                lista.append({
                    "hora": dt_p.strftime('%H:%M'), "data": dt_p.strftime('%d/%m'),
                    "temp": round(dados['temperature_2m'][i], 1), "umid": dados['relative_humidity_2m'][i],
                    "vento": round(dados['wind_speed_10m'][i], 1),
                    "chuva_p": dados['precipitation_probability'][i], "chuva_m": dados['precipitation'][i]
                })
        return lista
    except: return None

def gerar_texto_whatsapp(cidade, produto, classe, modalidade, dados_hora):
    texto = f"*🌱 TECPULVER BRASIL - RELATÓRIO TÉCNICO*\n"
    texto += f"📍 *Local:* {cidade}\n"
    texto += f"📦 *Produto:* {produto} ({classe})\n"
    texto += f"🚜 *Modalidade:* {modalidade}\n"
    texto += f"----------------------------\n"
    texto += f"🕒 *Janela Recomendada:* {dados_hora['hora']} ({dados_hora['data']})\n"
    texto += f"🌡️ *Temp:* {dados_hora['temp']}°C | 💧 *UR:* {dados_hora['umid']}%\n"
    texto += f"💨 *Vento:* {dados_hora['vento']} km/h\n"
    texto += f"📐 *Delta T:* {dados_hora['delta_t']}\n"
    texto += f"🌧️ *Risco Chuva:* {dados_hora['chuva_p']}%\n"
    texto += f"----------------------------\n"
    texto += f"✅ *Status:* APLICAÇÃO IDEAL"
    return urllib.parse.quote(texto)

# --- 4. CONTROLE DE ACESSO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<div class='login-wrapper'>", unsafe_allow_html=True)
    exibir_logo_padrao()
    st.markdown("<h2 style='text-align:center;'>TecPulver Brasil</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown("""
            <div class="beneficios-box">
                <div class="beneficio-item">✅ Janela Técnica 24h</div>
                <div class="beneficio-item">✅ Monitoramento Risco de Chuva</div>
                <div class="beneficio-item">✅ Base Agrofit Foliar Turbo</div>
                <div class="dados-precisos">Baseado em dados meteorológicos de precisão</div>
            </div>
        """, unsafe_allow_html=True)
        
        email = st.text_input("E-mail para acesso (30 dias grátis):", placeholder="ex: seuemail@dominio.com")
        if st.button("🚀 INICIAR OPERAÇÃO", use_container_width=True):
            if "@" in email and "." in email: 
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Por favor, insira um e-mail válido.")
        exibir_link_erro()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 5. INTERFACE PRINCIPAL (OTIMIZADA PARA CELULAR) ---
# Em vez de colunas lado a lado, usamos uma sequência vertical

# Cabeçalho Centralizado
st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
exibir_logo_padrao()
st.markdown("<h1>TecPulver Brasil</h1>", unsafe_allow_html=True)
st.caption("Inteligência e Precisão Meteorológica")
st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# 1. Localização (Vertical)
uf_sel = st.selectbox("📍 ESTADO:", ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"], index=15)

try:
    res_cid = requests.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sel}/municipios")
    cidades = sorted([m['nome'] for m in res_cid.json()]) if res_cid.status_code == 200 else []
except: cidades = []

cid_sel = st.selectbox("🏙️ CIDADE:", cidades, index=None, placeholder="Selecione o município...")

st.markdown("---")

# 2. Configuração da Aplicação (Vertical)
classe_sel = st.selectbox("🧪 CLASSE QUÍMICA:", ["Herbicidas", "Fungicidas", "Inseticidas", "Reguladores", "Adjuvantes/Outros"])

banco = carregar_produtos_turbo(classe_sel)
prod_sel = st.selectbox(f"📦 PRODUTO ({classe_sel}):", options=banco, index=None, placeholder="Busca rápida Agrofit...")

tipo_app = st.radio("🚜 MODALIDADE DE APLICAÇÃO:", ["Terrestre", "Aérea"], horizontal=True)

st.divider()

# --- 6. PROCESSAMENTO E TABELA DE RESULTADOS ---
if cid_sel and prod_sel:
    clima = buscar_clima_24h(cid_sel, uf_sel)
    if clima:
        st.markdown(f"### 🛰️ Planejamento Técnico: {cid_sel}")
        for p in clima:
            dt = round((p['temp'] * 0.75) - (p['umid'] * 0.15), 1)
            chuva_veta = p['chuva_p'] > 30 or p['chuva_m'] > 0.5
            
            if "Aérea" in tipo_app:
                ideal = (3.0 <= p['vento'] <= 10.0) and (2.0 <= dt <= 7.0) and not chuva_veta
            else:
                ideal = (2.0 <= p['vento'] <= 12.0) and (2.0 <= dt <= 8.5) and not chuva_veta
            
            st_txt, st_class = ("IDEAL", "status-ideal") if ideal else ("INADEQUADO", "status-critico")
            
            l1, l2, l3 = st.columns([1, 1, 2])
            l1.write(f"**{p['hora']}**<br><small>{p['data']}</small>", unsafe_allow_html=True)
            l2.markdown(f"<span class='{st_class}'>{st_txt}</span>", unsafe_allow_html=True)
            with l3:
                with st.expander("Ver Parâmetros"):
                    st.write(f"🌡️ Temp: {p['temp']}°C | 💧 UR: {p['umid']}%")
                    st.write(f"💨 Vento: {p['vento']} km/h | 📐 ΔT: {dt}")
                    
                    if ideal:
                        p['delta_t'] = dt
                        msg_zap = gerar_texto_whatsapp(cid_sel, prod_sel, classe_sel, tipo_app, p)
                        st.markdown(f"""
                            <a href="https://api.whatsapp.com/send?text={msg_zap}" target="_blank" style="text-decoration:none;">
                                <div style="background-color:#25D366; color:white; text-align:center; padding:8px; border-radius:5px; font-weight:bold; margin-top:10px;">
                                    📲 Enviar para Operador
                                </div>
                            </a>
                        """, unsafe_allow_html=True)
            st.markdown("<hr style='margin:0; opacity:0.1;'>", unsafe_allow_html=True)
    else:
        st.warning("Aguardando conexão com satélites meteorológicos...")

exibir_link_erro()