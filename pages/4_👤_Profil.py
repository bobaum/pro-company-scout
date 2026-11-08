import streamlit as st
from supabase import create_client
import PyPDF2
import io

st.set_page_config(page_title="Profil", page_icon="👤", layout="wide")

st.title("👤 Mein Kandidaten Profil")
st.markdown("Verwalte hier deinen Lebenslauf und deine Karriereziele. Je präziser diese Daten sind, desto schärfer wird die Skill Gap Analyse der KI.")

# --- DATENBANK ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = get_db()

# --- STATE MANAGEMENT ---
if "lebenslauf_text" not in st.session_state:
    st.session_state.lebenslauf_text = ""
if "skills_text" not in st.session_state:
    st.session_state.skills_text = ""
if "ziele_text" not in st.session_state:
    st.session_state.ziele_text = ""

# Daten laden beim ersten Start
if supabase and not st.session_state.lebenslauf_text and not st.session_state.skills_text and not st.session_state.ziele_text:
    try:
        res = supabase.table("profil").select("*").eq("id", 1).execute()
        if res.data:
            profil = res.data[0]
            st.session_state.lebenslauf_text = profil.get("lebenslauf", "")
            st.session_state.skills_text = profil.get("skills", "")
            st.session_state.ziele_text = profil.get("ziele", "")
    except Exception:
        pass

# --- NEUES LAYOUT ---
# Linke Spalte bekommt mehr Platz (Ratio 3 zu 2)
col1, col2 = st.columns([3, 2], gap="large")

with col1:
    st.subheader("📄 1. Lebenslauf Import und Editor")
    
    uploaded_file = st.file_uploader("Lade ein PDF hoch, um den Text automatisch zu extrahieren:", type="pdf")
    
    if uploaded_file is not None:
        try:
            reader = PyPDF2.PdfReader(uploaded_file)
            extracted_text = ""
            for page in reader.pages:
                extracted_text += page.extract_text() + "\n"
            st.session_state.lebenslauf_text = extracted_text
            st.toast("PDF erfolgreich ausgelesen!", icon="✅")
        except Exception as e:
            st.error(f"Fehler beim Lesen des PDFs: {e}")

    # Das Textfeld ist jetzt links und riesig
    lebenslauf_input = st.text_area(
        "Lebenslauf im Textformat:", 
        value=st.session_state.lebenslauf_text, 
        height=600,
        key="ll_area"
    )

with col2:
    st.subheader("🎯 2. Skills und Karriereziele")
    
    skills_input = st.text_area(
        "Besondere Hard und Soft Skills:", 
        value=st.session_state.skills_text, 
        height=250,
        key="sk_area"
    )
    
    ziele_input = st.text_area(
        "Karriereziele und Präferenzen:", 
        value=st.session_state.ziele_text, 
        height=250,
        key="zl_area"
    )
    
    st.write("") 
    if st.button("💾 Profil in Cloud speichern", type="primary", use_container_width=True):
        if supabase:
            try:
                data = {
                    "id": 1,
                    "lebenslauf": lebenslauf_input,
                    "skills": skills_input,
                    "ziele": ziele_input
                }
                supabase.table("profil").upsert(data).execute()
                
                st.session_state.lebenslauf_text = lebenslauf_input
                st.session_state.skills_text = skills_input
                st.session_state.ziele_text = ziele_input
                
                st.success("Profil erfolgreich aktualisiert!")
                st.toast("Daten in Supabase gespeichert", icon="🚀")
            except Exception as e:
                st.error(f"Speicherfehler: {e}")
        else:
            st.error("Keine Datenbankverbindung.")
