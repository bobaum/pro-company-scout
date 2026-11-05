import streamlit as st
import PyPDF2
from supabase import create_client

st.set_page_config(page_title="Mein Profil", page_icon="👤", layout="wide")
st.title("👤 Mein Profil & Lebenslauf")
st.markdown("Hinterlege hier deinen Lebenslauf und deine Skills. Die KI greift für jede Analyse live auf diese Daten zu.")

# --- DATENBANK-VERBINDUNG ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = get_db()

if not supabase:
    st.error("⚠️ Datenbankverbindung fehlt.")
    st.stop()

# --- AKTUELLE DATEN LADEN ---
try:
    profil_response = supabase.table("profil").select("*").eq("id", 1).execute()
    current_cv = profil_response.data[0].get("lebenslauf", "") if profil_response.data else ""
    current_skills = profil_response.data[0].get("skills", "") if profil_response.data else ""
    current_ziele = profil_response.data[0].get("ziele", "") if profil_response.data else ""
except Exception as e:
    st.error(f"Fehler beim Laden des Profils: {e}")
    current_cv, current_skills, current_ziele = "", "", ""

# --- PDF UPLOAD ---
st.subheader("1. Lebenslauf einlesen")
uploaded_file = st.file_uploader("📄 Lebenslauf als PDF hochladen (optional)", type="pdf")

if uploaded_file is not None:
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
        if extracted_text.strip():
            current_cv = extracted_text
            st.success("✅ PDF erfolgreich ausgelesen! Der Text wurde unten in das Feld eingefügt.")
    except Exception as e:
        st.error(f"Fehler beim Lesen des PDFs: {e}")

st.divider()

# --- PROFIL FORMULAR ---
st.subheader("2. Profil bearbeiten & speichern")
with st.form("profil_form"):
    input_cv = st.text_area("📄 Dein Lebenslauf-Text (aus PDF oder manuell):", value=current_cv, height=300)
    input_skills = st.text_input("🛠️ Zusätzliche Tech- & Soft-Skills (kommasepariert):", value=current_skills, placeholder="z.B. Python, Streamlit, Supabase, IT-Support")
    input_ziele = st.text_input("🎯 Karriereziele:", value=current_ziele, placeholder="z.B. IT-Consulting Praktikum in Dublin oder Osnabrück")
    
    submitted = st.form_submit_button("💾 Profil in Cloud speichern", type="primary")
    
    if submitted:
        profil_data = {
            "id": 1, 
            "lebenslauf": input_cv, 
            "skills": input_skills, 
            "ziele": input_ziele
        }
        try:
            supabase.table("profil").upsert(profil_data).execute()
            st.success("✅ Dein Profil wurde erfolgreich in der Cloud aktualisiert!")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")
