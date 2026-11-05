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
    # Neues, modernes Google SDK
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    api_bereit = True
except Exception:
    api_bereit = False

# --- SESSION STATE ABFRAGEN (Der nahtlose Übergang) ---
prefill_company = st.session_state.get("analyze_company_name", "")
prefill_details = st.session_state.get("analyze_company_details", "")

if prefill_company:
    st.info(f"💡 Unternehmen aus dem Live Scout übernommen: **{prefill_company}**")

# --- ANALYSE FORMULAR ---
ziel_unternehmen = st.text_input("Ziel-Unternehmen:", value=prefill_company)
stellen_details = st.text_area("Details zum Unternehmen / zur Stelle:", value=prefill_details, height=100)

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
                    1. **Matching Hard- & Soft-Skills:** Was bringt der Bewerber perfekt für dieses Unternehmen mit?
                    2. **Der Skill-Gap:** Welche Anforderungen fehlen ihm noch?
                    3. **Handlungsempfehlung:** Wie kann er diese Lücke bei einer Initiativbewerbung strategisch kaschieren?
                    """
                    
                    # Aufruf über das neue SDK
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=prompt,
                    )
                    antwort = response.text
                    
                    st.success("✅ Analyse erfolgreich abgeschlossen!")
                    
                    with st.container(border=True):
                        st.markdown(antwort)
                    
                    # Speicher leeren, nachdem die Analyse durch ist
                    st.session_state.analyze_company_name = ""
                    st.session_state.analyze_company_details = ""
                    
            except Exception as e:
                st.error(f"Fehler bei der Datenbank- oder KI-Abfrage: {e}")
