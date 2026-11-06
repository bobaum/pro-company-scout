import streamlit as st
from google import genai
from supabase import create_client

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

# --- DER TRESOR (Gegen das Verschwinden beim Tab-Wechsel) ---
if "saved_ziel" not in st.session_state:
    st.session_state.saved_ziel = ""
if "saved_details" not in st.session_state:
    st.session_state.saved_details = ""
if "ki_ergebnis" not in st.session_state:
    st.session_state.ki_ergebnis = ""

# Teleport-Übergabe aus der Suche oder Pipeline abfangen
if st.session_state.get("analyze_company_name"):
    st.session_state.saved_ziel = st.session_state.analyze_company_name
    st.session_state.saved_details = st.session_state.analyze_company_details
    st.session_state.ki_ergebnis = "" # Altes Ergebnis löschen bei neuer Firma
    st.session_state.analyze_company_name = ""
    st.session_state.analyze_company_details = ""

# Diese Funktion sichert manuelles Tippen sofort im Tresor
def sync_inputs():
    st.session_state.saved_ziel = st.session_state.widget_ziel
    st.session_state.saved_details = st.session_state.widget_details
    st.session_state.ki_ergebnis = "" # KI-Text löschen, wenn User die Firma ändert

if st.session_state.saved_ziel:
    st.info(f"💡 Aktuelles Ziel-Unternehmen im Fokus: **{st.session_state.saved_ziel}**")

# --- ANALYSE FORMULAR (An den Tresor gekoppelt) ---
ziel_unternehmen = st.text_input(
    "Ziel-Unternehmen:", 
    value=st.session_state.saved_ziel, 
    key="widget_ziel", 
    on_change=sync_inputs
)
stellen_details = st.text_area(
    "Details zum Unternehmen / zur Stelle:", 
    value=st.session_state.saved_details, 
    key="widget_details", 
    height=100, 
    on_change=sync_inputs
)

# --- ZWEI BUTTONS NEBENEINANDER ---
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
        # UX-Hinweis, dass man nicht wegklicken darf
        with st.spinner("Gemini analysiert dein Profil... (Bitte bleibe kurz auf dieser Seite)"):
            try:
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
                    Details: '{stellen_details}'
                    
                    Führe eine prägnante Skill-Gap-Analyse durch (Nutze Bulletpoints):
                    1. **Matching Hard- & Soft-Skills:** Was bringt der Bewerber perfekt für dieses Unternehmen mit?
                    2. **Der Skill-Gap:** Welche Anforderungen fehlen ihm noch?
                    3. **Handlungsempfehlung:** Wie kann er diese Lücke bei einer Initiativbewerbung strategisch kaschieren?
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt,
                    )
                    
                    # KI ERGEBNIS DAUERHAFT IM TRESOR SPEICHERN
                    st.session_state.ki_ergebnis = response.text
                    st.success("✅ Analyse erfolgreich abgeschlossen!")
                    
            except Exception as e:
                st.error(f"Fehler bei der KI-Abfrage: {e}")

# --- KI ERGEBNIS ANZEIGEN (Bleibt auch nach Tab-Wechsel sichtbar) ---
if st.session_state.ki_ergebnis:
    with st.container(border=True):
        st.markdown(st.session_state.ki_ergebnis)
