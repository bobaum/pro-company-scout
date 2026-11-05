import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai

# --- 1. SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Personal Job Scout", page_icon="🎯", layout="wide")

# --- 2. SESSION STATE INITIALISIEREN (Das Gedächtnis der App) ---
# Hier speichern wir Firmen zwischen, um sie nahtlos von der Suche in die Analyse zu übergeben
if "analyze_company_name" not in st.session_state:
    st.session_state.analyze_company_name = ""
if "analyze_company_details" not in st.session_state:
    st.session_state.analyze_company_details = ""

# --- 3. APIs & DATENBANK VERBINDEN ---
@st.cache_resource
def init_connections():
    status = {"gemini": False, "places": False, "supabase": False, "db": None}
    
    # Supabase Cloud-Datenbank
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        status["db"] = create_client(url, key)
        status["supabase"] = True
    except Exception:
        pass
        
    # Google Gemini AI
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        status["gemini"] = True
    except Exception:
        pass

    # Google Places API
    try:
        if "PLACES_API_KEY" in st.secrets:
            status["places"] = True
    except Exception:
        pass
        
    return status

# Verbindungen einmalig beim Start aufbauen
sys_status = init_connections()

# --- 4. STARTSEITE / DASHBOARD ---
st.title("🎯 Personal Job Scout: Bo Baumann")
st.markdown("Willkommen in deinem cloudbasierten Karriere-CRM. Wähle links in der Seitenleiste ein Modul aus.")

st.divider()

# Professioneller System-Check mit Metriken
st.subheader("⚙️ System-Status")
col1, col2, col3 = st.columns(3)
col1.metric("Cloud Datenbank (Supabase)", "Verbunden 🟢" if sys_status["supabase"] else "Getrennt 🔴")
col2.metric("KI Engine (Gemini)", "Bereit 🟢" if sys_status["gemini"] else "Fehlt 🔴")
col3.metric("Live Scout (Google Places)", "Bereit 🟢" if sys_status["places"] else "Fehlt 🔴")

st.info("👈 Sobald wir die Unterseiten angelegt haben, erscheint hier links automatisch deine Navigation.")
