import streamlit as st
import requests
from supabase import create_client
from google import genai

st.set_page_config(page_title="KI Analyse", page_icon="🧠", layout="wide")

st.title("KI Unternehmens- & Skill-Gap-Analyse")
st.markdown("Analysiere die Webseite eines potenziellen Arbeitgebers im Abgleich mit deinem Profil und generiere ein passgenaues Anschreiben.")

# --- DATENBANK & KI INITIALISIERUNG ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Datenbank-Verbindungsfehler: {e}")
        return None

@st.cache_resource
def get_gemini():
    try:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.error(f"Gemini API Fehler: {e}")
        return None

supabase = get_db()
gemini_client = get_gemini()

if not supabase:
    st.stop()

# --- PROFIL AUS SUPABASE LADEN ---
def load_user_profile():
    try:
        res = supabase.table("profil").select("*").limit(1).execute()
        if res.data:
            return res.data[0]
        return {}
    except Exception as e:
        st.warning(f"Profil konnte nicht geladen werden: {e}")
        return {}

profil = load_user_profile()

# --- EXAKTE SESSION STATE ÜBERNAHME AUS DEM LIVE SCOUT ---
default_company = st.session_state.get("analyze_company_name", "")
default_url = st.session_state.get("analyze_company_url", "")
company_details = st.session_state.get("analyze_company_details", "")

if company_details:
    st.info(f"Übernommene Scout-Infos: {company_details.replace(chr(10), ' | ')}")

# --- EINGABEBEREICH ---
col1, col2 = st.columns(2)
with col1:
    unternehmen = st.text_input("Unternehmensname *", value=default_company, placeholder="z. B. noventum consulting GmbH")
    ziel_rolle = st.text_input("Angestrebte Rolle / Bereich", value="Werkstudent / Praktikum IT-Consulting & PMO")
with col2:
    webseite = st.text_input("Webseite (URL) *", value=default_url, placeholder="https://www.beispiel-firma.de")
    ansprechpartner = st.text_input("Ansprechpartner (optional)", placeholder="z. B. Max Mustermann (HR / Fachbereich)")

# --- HELPER: WEBSEITE VIA JINA READER AUSLESEN ---
def scrape_website_jina(url):
    if not url.startswith("http"):
        url = "https://" + url
    jina_url = f"https://r.jina.ai/{url}"
    try:
        response = requests.get(jina_url, timeout=15)
        if response.status_code == 200:
            return response.text[:15000]
        return None
    except Exception:
        return None

# --- ANALYSE STARTEN ---
if st.button("Unternehmen analysieren & Match berechnen", type="primary", width="stretch"):
    if not unternehmen or not webseite:
        st.warning("Bitte gib mindestens den Unternehmensnamen und die Webseite an.")
    elif not gemini_client:
        st.error("Kein gültiger Gemini API Key hinterlegt.")
    else:
        with st.spinner(f"Lese Webseite von {unternehmen} aus und führe KI-Analyse durch..."):
            website_text = scrape_website_jina(webseite)
            
            if not website_text:
                st.error("Die Webseite konnte nicht automatisch ausgelesen werden. Prüfe die URL oder versuche eine Unterseite (z. B. /karriere).")
            else:
                profil_text = (
                    f"Name: {profil.get('name', 'Bo Baumann')}\n"
                    f"Studium: {profil.get('studium', 'B.Sc. Wirtschaftsinformatik (Hochschule Osnabrück)')}\n"
                    f"Erfahrung: {profil.get('erfahrung', 'Junior IT-Administrator (IT Operations, Support für 50+ User)')}\n"
                    f"Skills: {profil.get('skills', 'Python, Streamlit, PostgreSQL/Supabase, REST APIs, IT-Service-Management, Prozessanalyse')}\n"
                    f"Fokus: {profil.get('fokus', 'PMO, IT-Consulting, Business Analysis, Schnittstelle Business & IT')}"
                )
                
                prompt = (
                    "Du bist ein erfahrener Karriere-Coach und Senior IT-Consultant.\n"
                    "Analysiere das folgende Unternehmen anhand seiner Webseiten-Inhalte und gleiche es mit dem Bewerberprofil ab.\n\n"
                    f"UNTERNEHMEN: {unternehmen}\n"
                    f"ZUSATZINFOS (STANDORT/BRANCHE): {company_details}\n"
                    f"ANGESTREBTE ROLLE: {ziel_rolle}\n"
                    f"WEBSEITEN-INHALT (Auszug):\n{website_text}\n\n"
                    f"BEWERBERPROFIL:\n{profil_text}\n\n"
                    "Strukturiere deine Antwort exakt in diese vier Abschnitte (kurz, präzise, ohne leere Floskeln):\n"
                    "1. **Unternehmensfokus & Kerngeschäft:** Was macht die Firma konkret (Branche, Tech-Stack, Beratungsschwerpunkte)?\n"
                    "2. **Match-Score & Stärken-Abgleich (0-100 %):** Warum passt das Profil (Wirtschaftsinformatik + IT-Admin-Praxis + Cloud-Projekte) zu diesem Unternehmen?\n"
                    "3. **Skill-Gaps & Gesprächsvorbereitung:** Worauf sollte sich der Bewerber im Gespräch besonders vorbereiten oder welche Themen sollte er aktiv ansprechen?\n"
                    "4. **Individueller Anschreiben-Entwurf:** Ein moderner, direkter und geerdeter Entwurf (max. 180 Wörter) ohne ver
