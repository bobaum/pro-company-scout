import streamlit as st
from google import genai
from supabase import create_client
import time
import random
import requests # NEU: Für den Web-Scraper

st.set_page_config(page_title="KI-Analyse", page_icon="🧠", layout="wide")
st.title("🧠 KI Skill-Gap Analyse")
st.markdown("Lass die KI berechnen, wie gut dein Profil zu diesem Unternehmen passt.")

# --- DATENBANK & API ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = get_db()

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    api_bereit = True
except Exception:
    api_bereit = False

# --- DER TRESOR (State Management) ---
if "saved_ziel" not in st.session_state:
    st.session_state.saved_ziel = ""
if "saved_details" not in st.session_state:
    st.session_state.saved_details = ""
if "saved_url" not in st.session_state: # NEU: URL im Tresor
    st.session_state.saved_url = ""
if "ki_ergebnis" not in st.session_state:
    st.session_state.ki_ergebnis = ""

# Teleport-Übergabe aus der Suche abfangen
if st.session_state.get("analyze_company_name"):
    st.session_state.saved_ziel = st.session_state.analyze_company_name
    st.session_state.saved_details = st.session_state.analyze_company_details
    st.session_state.saved_url = "" 
    st.session_state.ki_ergebnis = "" 
    st.session_state.analyze_company_name = ""
    st.session_state.analyze_company_details = ""

def sync_inputs():
    st.session_state.saved_ziel = st.session_state.widget_ziel
    st.session_state.saved_details = st.session_state.widget_details
    st.session_state.saved_url = st.session_state.widget_url # NEU
    st.session_state.ki_ergebnis = "" 

if st.session_state.saved_ziel:
    st.info(f"💡 Aktuelles Ziel-Unternehmen im Fokus: **{st.session_state.saved_ziel}**")

# --- ANALYSE FORMULAR ---
ziel_unternehmen = st.text_input(
    "Ziel-Unternehmen:", 
    value=st.session_state.saved_ziel, 
    key="widget_ziel", 
    on_change=sync_inputs
)

# NEU: Das URL Eingabefeld
unternehmens_url = st.text_input(
    "Webseite (URL) des Unternehmens (optional für bessere KI-Analyse):", 
    value=st.session_state.saved_url,
    key="widget_url",
    placeholder="z.B. https://www.firma.de",
    on_change=sync_inputs
)

stellen_details = st.text_area(
    "Details zum Unternehmen / zur Stelle:", 
    value=st.session_state.saved_details, 
    key="widget_details", 
    height=100, 
    on_change=sync_inputs
)

# --- BUTTONS ---
btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    analyze_clicked = st.button("🚀 KI-Analyse starten", type="primary", use_container_width=True)

with btn_col2:
    add_to_pipeline_clicked = st.button("➕ In Pipeline speichern", use_container_width=True)

# 1. Logik: Zur Pipeline hinzufügen
if add_to_pipeline_clicked:
    if not supabase:
        st.error("⚠️ Datenbankverbindung fehlt.")
    elif not ziel_unternehmen:
        st.warning("Bitte gib ein Ziel-Unternehmen ein.")
    else:
        new_entry = {"unternehmen": ziel_unternehmen, "rolle": "Initiativ", "status": "Neu", "notizen": stellen_details}
        try:
            supabase.table("pipeline").insert(new_entry).execute()
            st.toast(f"✅ {ziel_unternehmen} wurde in der Pipeline gespeichert!", icon="💾")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")

# 2. Logik: KI Analyse starten
if analyze_clicked:
    if not api_bereit:
        st.error("⚠️ Gemini API-Schlüssel fehlt.")
    elif not supabase:
        st.error("⚠️ Datenbankverbindung fehlt.")
    elif not ziel_unternehmen:
        st.warning("Bitte gib ein Ziel-Unternehmen ein.")
    else:
        with st.spinner("Sammle Daten und analysiere dein Profil..."):
            try:
                # --- NEU: Web-Scraper Logik (Jina Reader) ---
                gesammelter_web_text = ""
                if unternehmens_url:
                    st.toast("Lese Webseite aus...", icon="🌐")
                    try:
                        # Wir setzen einfach r.jina.ai vor die URL!
                        r = requests.get(f"https://r.jina.ai/{unternehmens_url}", timeout=10)
                        if r.status_code == 200:
                            # Wir nehmen max 5000 Zeichen, um Token-Limits zu schonen (FinOps)
                            gesammelter_web_text = r.text[:5000] 
                            st.toast("Webseite erfolgreich gelesen!", icon="✅")
                    except:
                        st.warning("Konnte Webseite nicht auslesen. Mache ohne weiter.")

                profil_response = supabase.table("profil").select("*").eq("id", 1).execute()
                
                if not profil_response.data or not profil_response.data[0].get("lebenslauf"):
                    st.error("⚠️ Kein Lebenslauf gefunden. Bitte fülle zuerst dein Profil aus.")
                else:
                    mein_profil = profil_response.data[0]
                    
                    prompt = f"""
                    Du bist ein technischer Karriere-Scout.
                    
                    Hier ist der detaillierte Lebenslauf und das Profil des Bewerbers:
                    Lebenslauf: {mein_profil.get('lebenslauf', 'Nicht angegeben')}
                    Zusätzliche Skills: {mein_profil.get('skills', 'Nicht angegeben')}
                    Karriereziele: {mein_profil.get('ziele', 'Nicht angegeben')}
                    
                    Ziel-Unternehmen & Rolle: '{ziel_unternehmen}'
                    Manuelle Details: '{stellen_details}'
                    Extrahierter Text von der Webseite: '{gesammelter_web_text}'
                    
                    Führe eine prägnante Skill-Gap-Analyse durch (Nutze Bulletpoints):
                    1. **Matching Hard- & Soft-Skills:** Was bringt der Bewerber perfekt für dieses Unternehmen mit?
                    2. **Der Skill-Gap:** Welche Anforderungen fehlen ihm noch?
                    3. **Handlungsempfehlung:** Wie kann er diese Lücke bei einer Initiativbewerbung strategisch kaschieren?
                    """
                    
                    # --- SMART CALL LOGIC ---
                    fallback_models = ["gemini-3.8-pro", "gemini-3.8-flash", "gemini-2.0-flash"]
                    max_retries = 3
                    erfolg = False
                    status_placeholder = st.empty()

                    for model_name in fallback_models:
                        if erfolg:
                            break
                        for attempt in range(max_retries):
                            try:
                                response = client.models.generate_content(
                                    model=model_name,
                                    contents=prompt,
                                )
                                st.session_state.ki_ergebnis = response.text
                                status_placeholder.empty() 
                                st.success(f"✅ Analyse mit {model_name} erfolgreich abgeschlossen!")
                                erfolg = True
                                break 
                            except Exception as e:
                                error_msg = str(e)
                                if "503" in error_msg or "429" in error_msg:
                                    if attempt < max_retries - 1:
                                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                                        status_placeholder.warning(f"⏳ Server ausgelastet (503). Versuch {attempt+1}... Warte {wait_time:.1f}s")
                                        time.sleep(wait_time)
                                    else:
                                        status_placeholder.error(f"⚠️ {model_name} ist überlastet. Wechsle zum Fallback-Modell...")
                                elif "404" in error_msg:
                                    status_placeholder.warning(f"⚠️ Modell {model_name} noch nicht verfügbar. Wechsle zum Fallback...")
                                    break
                                else:
                                    st.error(f"Unerwarteter Fehler bei der KI-Abfrage: {error_msg}")
                                    break 
                                    
                    if not erfolg:
                        st.error("❌ Alle Modelle sind aktuell überlastet. Bitte probiere es in ein paar Minuten erneut.")
                        
            except Exception as e:
                st.error(f"Fehler beim Laden des Profils: {e}")

# --- KI ERGEBNIS ANZEIGEN ---
if st.session_state.ki_ergebnis:
    with st.container(border=True):
        st.markdown(st.session_state.ki_ergebnis)
