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

# --- SESSION STATE & WIDGET SYNC ---
# Wenn aus dem Live Scout eine Firma übergeben wurde, überschreiben wir die Felder
if "analyze_company_name" in st.session_state and st.session_state.analyze_company_name:
    st.session_state.ziel_input = st.session_state.analyze_company_name
    st.session_state.details_input = st.session_state.analyze_company_details
    # Anschliessend leeren, damit man manuell weiterschreiben kann
    st.session_state.analyze_company_name = ""
    st.session_state.analyze_company_details = ""

# Standardwerte im Session State initialisieren, falls leer
if "ziel_input" not in st.session_state:
    st.session_state.ziel_input = ""
if "details_input" not in st.session_state:
    st.session_state.details_input = ""

if st.session_state.ziel_input:
    st.info(f"💡 Aktuelles Ziel-Unternehmen im Fokus: **{st.session_state.ziel_input}**")

# --- ANALYSE FORMULAR (Mit festem Key gekoppelt) ---
ziel_unternehmen = st.text_input("Ziel-Unternehmen:", key="ziel_input")
stellen_details = st.text_area("Details zum Unternehmen / zur Stelle:", key="details_input", height=100)

if st.button("🚀 KI-Analyse starten", type="primary"):
    if not api_bereit:
        st.error("⚠️ Gemini API-Schlüssel fehlt.")
    elif not supabase:
        st.error("⚠️ Datenbankverbindung fehlt.")
    elif not ziel_unternehmen:
        st.warning("Bitte gib ein Ziel-Unternehmen ein.")
    else:
        with st.spinner("Gemini analysiert dein Profil..."):
            try:
                # Aktuelles Profil aus Supabase laden
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
                    1. **Matching Hard- & Soft-Skills:** Was bringt the Bewerber perfekt für dieses Unternehmen mit?
                    2. **Der Skill-Gap:** Welche Anforderungen fehlen ihm noch?
                    3. **Handlungsempfehlung:** Wie kann er diese Lücke bei einer Initiativbewerbung strategisch kaschieren?
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=prompt,
                    )
                    antwort = response.text
                    
                    st.success("✅ Analyse erfolgreich abgeschlossen!")
                    
                    with st.container(border=True):
                        st.markdown(antwort)
                    
            except Exception as e:
                st.error(f"Fehler bei der Datenbank- oder KI-Abfrage: {e}")
