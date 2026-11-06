import streamlit as st
from supabase import create_client
import PyPDF2

st.set_page_config(page_title="Mein Profil", page_icon="👤", layout="wide")
st.title("👤 Mein Kandidaten-Profil")
st.markdown("Verwalte hier deinen Lebenslauf und deine Karriereziele. Je präziser diese Daten sind, desto schärfer wird die Skill-Gap Analyse der KI.")

# --- SESSION STATE FÜR ERFOLGSMELDUNG ---
if "profil_save_success" not in st.session_state:
    st.session_state.profil_save_success = False

if st.session_state.profil_save_success:
    st.toast("✅ Profil erfolgreich in der Cloud aktualisiert!", icon="💾")
    st.success("✅ Profil gespeichert!")
    st.session_state.profil_save_success = False

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

# --- DATEN LADEN ---
try:
    response = supabase.table("profil").select("*").eq("id", 1).execute()
    # Wenn Daten da sind, nehmen wir sie, sonst leere Felder
    profil_daten = response.data[0] if response.data else {"lebenslauf": "", "skills": "", "ziele": ""}
except Exception as e:
    st.error(f"Fehler beim Laden des Profils: {e}")
    profil_daten = {"lebenslauf": "", "skills": "", "ziele": ""}

# --- LAYOUT: 2 SPALTEN ARCHITEKTUR ---
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📄 1. PDF-Lebenslauf Import")
    st.info("Lade ein PDF hoch, um den Text automatisch extrahieren zu lassen. Du kannst ihn danach rechts bearbeiten.")
    
    uploaded_file = st.file_uploader("Lebenslauf (PDF-Format)", type=["pdf"])
    extracted_text = ""
    
    if uploaded_file is not None:
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
                    
            st.success("✅ PDF erfolgreich ausgelesen!")
            with st.expander("Gelesenen Text anzeigen (Rohdaten)"):
                st.text(extracted_text)
                st.caption("Tipp: Wenn du den Text rechts im Editor speicherst, wird er für die KI übernommen.")
        except Exception as e:
            st.error(f"Fehler beim Lesen des PDFs: {e}")

with col2:
    st.subheader("✏️ 2. Mein Profil-Editor")
    
    with st.form("profil_form"):
        # Smarte Logik: Wenn gerade ein PDF hochgeladen wurde, füllen wir das Feld damit vor. 
        # Ansonsten laden wir den Stand aus der Datenbank.
        default_cv = extracted_text if extracted_text else profil_daten.get("lebenslauf", "")
        
        lebenslauf_input = st.text_area(
            "Lebenslauf (Textformat):", 
            value=default_cv, 
            height=250, 
            help="Überprüfe den extrahierten Text. Die KI liest genau das, was hier steht."
        )
        
        skills_input = st.text_area(
            "Besondere Hard- & Soft-Skills:", 
            value=profil_daten.get("skills", ""), 
            height=100,
            placeholder="z.B. IT-Operations, Projektmanagement, Python, Hardware-Rollout..."
        )
        
        ziele_input = st.text_area(
            "Karriereziele & Präferenzen:", 
            value=profil_daten.get("ziele", ""), 
            height=100,
            placeholder="z.B. Fokus auf IT-Consulting & PMO, keine reine Softwareentwicklung..."
        )
        
        submit_button = st.form_submit_button("💾 Profil in Cloud speichern", type="primary", use_container_width=True)
        
        if submit_button:
            update_data = {
                "id": 1,
                "lebenslauf": lebenslauf_input,
                "skills": skills_input,
                "ziele": ziele_input
            }
            try:
                # Upsert aktualisiert den Eintrag mit ID 1 oder legt ihn neu an
                supabase.table("profil").upsert(update_data).execute()
                st.session_state.profil_save_success = True
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern in Supabase: {e}")
