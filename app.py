import streamlit as st
import pandas as pd
from supabase import create_client
from google import genai

st.set_page_config(page_title="Personal Job Scout", page_icon="🎯", layout="wide")

st.title("🎯 Personal Job Scout: Bo Baumann")
st.markdown("Willkommen in deinem cloudbasierten Karriere-CRM. Hier ist dein aktueller Bewerbungs-Überblick.")

# --- DATENBANK ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = get_db()

# --- DASHBOARD & FUNNEL ---
st.header("📊 Dein Bewerbungs-Funnel")

if supabase:
    try:
        # Lerneffekt: Wir rufen alles ab (ohne .order) und sortieren clientseitig
        response = supabase.table("pipeline").select("*").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            # Metriken berechnen
            total = len(df)
            prep = len(df[df["status"] == "In Vorbereitung"])
            applied = len(df[df["status"] == "Beworben"])
            interviews = len(df[df["status"] == "Interview"])
            
            # Funnel visualisieren
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Gespeicherte Firmen", total)
            col2.metric("In Vorbereitung", prep)
            col3.metric("Laufende Bewerbungen", applied)
            col4.metric("Interviews", interviews)
            
            st.divider()
            
            # Zuletzt hinzugefügt: Wir drehen den Datensatz mit Pandas um [::-1]
            st.subheader("🕒 Die 5 neuesten Entdeckungen")
            df_reversed = df.iloc[::-1]
            
            st.dataframe(
                df_reversed[["unternehmen", "rolle", "status", "notizen"]].head(5), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Deine Pipeline ist noch leer. Nutze den Live Scout, um Unternehmen zu suchen!")
            
    except Exception as e:
        st.error(f"Fehler beim Laden des Dashboards: {e}")
else:
    st.error("⚠️ Keine Datenbankverbindung für das Dashboard.")

st.divider()

# --- SYSTEM-STATUS (Die technische Überwachung) ---
st.header("⚙️ System-Status")

system_fehler = []

# 1. Supabase Check
if not supabase:
    system_fehler.append("❌ Cloud Datenbank (Supabase): Verbindung getrennt")

# 2. Gemini Check
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    system_fehler.append("❌ KI Engine (Gemini API): Fehler oder Key fehlt")

# 3. Places API Check
if not st.secrets.get("PLACES_API_KEY"):
    system_fehler.append("❌ Live Scout (Google Places): API-Key fehlt")

# Ausgabe: Nur meckern, wenn etwas kaputt ist
if not system_fehler:
    st.success("✅ Alle Systeme einsatzbereit (Datenbank, KI & API-Schnittstellen)")
else:
    st.error("⚠️ System-Warnung: Folgende Module sind nicht bereit:")
    for fehler in system_fehler:
        st.warning(fehler)
        st.error("❌ Live Scout: API-Key fehlt")
