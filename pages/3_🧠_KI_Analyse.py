import time
import streamlit as st
import requests
from supabase import create_client
from google import genai

st.set_page_config(page_title="KI Analyse", page_icon="🧠", layout="wide")

st.title("KI Unternehmens- & Skill-Gap-Analyse")
st.markdown(
    "Analysiere die Webseite eines Arbeitgebers im Abgleich "
    "mit deinem Profil und generiere ein Anschreiben."
)

# --- DATENBANK & KI INITIALISIERUNG ---
@st.cache_resource
def get_db():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
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
    clean_details = company_details.replace("\n", " | ")
    st.info(f"Übernommene Scout-Infos: {clean_details}")

# --- EINGABEBEREICH ---
col1, col2 = st.columns(2)
with col1:
    unternehmen = st.text_input(
        "Unternehmensname *",
        value=default_company,
        placeholder="z. B. noventum consulting GmbH"
    )
    ziel_rolle = st.text_input(
        "Angestrebte Rolle / Bereich",
        value="Werkstudent / Praktikum IT-Consulting & PMO"
    )
with col2:
    webseite = st.text_input(
        "Webseite (URL) *",
        value=default_url,
        placeholder="https://www.beispiel-firma.de"
    )
    ansprechpartner = st.text_input(
        "Ansprechpartner (optional)",
        placeholder="z. B. Max Mustermann (HR / Fachbereich)"
    )

# --- HELPER: WEBSEITE VIA JINA READER AUSLESEN (MIT ROBUSTEM TIMEOUT) ---
def scrape_website_jina(url):
    if not url or url == "https://":
        return "Keine Webseiten-URL angegeben."
    if not url.startswith("http"):
        url = "https://" + url
    jina_url = f"https://r.jina.ai/{url}"
    try:
        # Harter Timeout nach 10 Sekunden, damit es nicht ewig hängt
        response = requests.get(jina_url, timeout=10)
        if response.status_code == 200:
            return response.text[:15000]
        return f"Webseite konnte nicht geladen werden (HTTP Status: {response.status_code})"
    except requests.exceptions.Timeout:
        return "Hinweis: Die Webseite hat zu lange geantwortet (Timeout). Die Analyse erfolgt basierend auf dem Unternehmensnamen und Standort."
    except Exception as e:
        return f"Konnte Webseiten-Inhalt nicht abrufen: {e}"

# --- HELPER: GEMINI MIT RETRY & FALLBACK ---
def generate_with_retry(client, prompt_text):
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3-flash-preview",
        "gemini-2.5-flash"
    ]
    last_error = None

    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_text
                )
                return response.text, model_name
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                    wait_sec = 2 * (attempt + 1)
                    st.toast(f"{model_name} ausgelastet – neuer Versuch in {wait_sec}s...")
                    time.sleep(wait_sec)
                else:
                    break

    raise RuntimeError(f"Alle Versuche fehlgeschlagen. Letzter Fehler: {last_error}")

# --- ANALYSE STARTEN ---
if st.button("Unternehmen analysieren & Match berechnen", type="primary", width="stretch"):
    if not unternehmen or not webseite:
        st.warning("Bitte gib mindestens Unternehmensnamen und Webseite an.")
    elif not gemini_client:
        st.error("Kein gültiger Gemini API Key hinterlegt.")
    else:
        with st.spinner(f"Lese Webseite von {unternehmen} aus und führe KI-Analyse durch..."):
            website_text = scrape_website_jina(webseite)

            if not website_text:
                st.error("Webseite konnte nicht ausgelesen werden. Prüfe die URL.")
            else:
                profil_lines = [
                    f"Name: {profil.get('name', 'Bo Baumann')}",
                    f"Studium: {profil.get('studium', 'B.Sc. Wirtschaftsinformatik')}",
                    f"Erfahrung: {profil.get('erfahrung', 'Junior IT-Administrator')}",
                    f"Skills: {profil.get('skills', 'Python, Streamlit, Supabase, REST APIs')}",
                    f"Fokus: {profil.get('fokus', 'PMO, IT-Consulting, Business Analysis')}"
                ]
                profil_text = "\n".join(profil_lines)

                prompt_lines = [
                    "Du bist ein erfahrener Karriere-Coach und Senior IT-Consultant.",
                    "Analysiere das Unternehmen anhand der Webseiten-Inhalte.",
                    "Gleiche es danach mit dem Bewerberprofil ab.",
                    "",
                    f"UNTERNEHMEN: {unternehmen}",
                    f"ZUSATZINFOS: {company_details}",
                    f"ANGESTREBTE ROLLE: {ziel_rolle}",
                    f"WEBSEITEN-INHALT:\n{website_text}",
                    "",
                    f"BEWERBERPROFIL:\n{profil_text}",
                    "",
                    "Strukturiere deine Antwort in exakt diese vier Abschnitte:",
                    "1. **Unternehmensfokus & Kerngeschäft:** Branche, Tech-Stack, Fokus.",
                    "2. **Match-Score (0-100 %):** Warum passt das Profil zur Firma?",
                    "3. **Skill-Gaps & Vorbereitung:** Worauf im Gespräch achten?",
                    "4. **Anschreiben-Entwurf:** Direkt, modern, max. 180 Wörter, ohne Floskeln."
                ]
                prompt = "\n".join(prompt_lines)

                try:
                    analysis_text, used_model = generate_with_retry(gemini_client, prompt)
                    st.session_state["last_analysis"] = analysis_text
                    st.session_state["last_model"] = used_model
                    st.session_state["last_company"] = unternehmen
                    st.session_state["last_role"] = ziel_rolle
                    st.session_state["last_contact"] = ansprechpartner
                except Exception as e:
                    st.error(f"Fehler bei der Gemini-Generierung: {e}")

# --- ERGEBNIS ANZEIGEN & IN PIPELINE SPEICHERN ---
if "last_analysis" in st.session_state and st.session_state["last_analysis"]:
    st.divider()
    firma_titel = st.session_state.get("last_company", unternehmen)
    st.subheader(f"Analyse-Ergebnis: {firma_titel}")
    if "last_model" in st.session_state:
        st.caption(f"Generiert mit Modell: `{st.session_state['last_model']}`")
    st.markdown(st.session_state["last_analysis"])

    st.divider()
    if st.button("In meine Pipeline übernehmen", type="secondary", width="stretch"):
        try:
            kurz_notiz = st.session_state["last_analysis"][:1000] + "..."
            pipeline_entry = {
                "unternehmen": st.session_state.get("last_company", unternehmen),
                "rolle": st.session_state.get("last_role", ziel_rolle),
                "ansprechpartner": st.session_state.get("last_contact", ansprechpartner),
                "status": "In Vorbereitung",
                "notizen": kurz_notiz
            }
            supabase.table("pipeline").insert(pipeline_entry).execute()
            st.toast(f"{pipeline_entry['unternehmen']} gespeichert!")
            st.success("Eintrag wurde in deiner Pipeline gespeichert.")
        except Exception as e:
            st.error(f"Fehler beim Speichern in der Pipeline: {e}")
