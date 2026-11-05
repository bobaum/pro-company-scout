import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Pipeline", page_icon="📈", layout="wide")
st.title("📈 Meine Bewerbungs-Pipeline")
st.markdown("Dein CRM-Board: Verwalte hier deine Favoriten und den Status deiner Initiativbewerbungen.")

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

# --- DATEN LADEN & KPIs BERECHNEN ---
try:
    response = supabase.table("pipeline").select("*").execute()
    df_pipeline = pd.DataFrame(response.data)
    
    if df_pipeline.empty:
        df_pipeline = pd.DataFrame(columns=["id", "unternehmen", "rolle", "status", "deadline", "notizen"])
        st.info("Noch keine Unternehmen in der Pipeline. Nutze den Live Scout, um welche hinzuzufügen!")
    else:
        # SaaS-Style KPIs berechnen
        total_saved = len(df_pipeline)
        active_applications = len(df_pipeline[df_pipeline["status"].isin(["Beworben", "In Vorbereitung", "Interview"])])
        interviews = len(df_pipeline[df_pipeline["status"] == "Interview"])
        
        # KPI Dashboard rendern
        st.subheader("📊 Pipeline Übersicht")
        col1, col2, col3 = st.columns(3)
        col1.metric("Gespeicherte Favoriten", total_saved)
        col2.metric("Aktive Bewerbungen", active_applications)
        col3.metric("Laufende Interviews", interviews)
        
        st.divider()
        
        # --- INTERAKTIVE TABELLE (Status-Board) ---
        st.subheader("📋 Status-Board")
        
        # Streamlit Data Editor mit typsicheren Spalten konfigurieren
        edited_df = st.data_editor(
            df_pipeline,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # Wir verstecken die Datenbank-ID, da sie für das UI irrelevant ist
                "unternehmen": st.column_config.TextColumn("Unternehmen", disabled=True), 
                "rolle": st.column_config.TextColumn("Rolle / Bereich"),
                "status": st.column_config.SelectboxColumn(
                    "Aktueller Status",
                    help="Wähle den aktuellen Stand deiner Bewerbung",
                    options=["Neu", "In Vorbereitung", "Beworben", "Interview", "Angebot", "Abgesagt", "On Hold"],
                    required=True
                ),
                "deadline": st.column_config.DateColumn("Deadline / Wiedervorlage"),
                "notizen": st.column_config.TextColumn("Notizen & Adresse")
            }
        )
        
        # Änderungen in die Cloud pushen
        if st.button("💾 Änderungen in Cloud speichern", type="primary"):
            valid_data = edited_df[edited_df["unternehmen"].astype(str).str.strip() != ""]
            records = valid_data.to_dict(orient="records")
            if records:
                supabase.table("pipeline").upsert(records).execute()
                st.success("✅ Pipeline erfolgreich aktualisiert!")
                st.rerun() # Lädt die Seite kurz neu, um die KPIs oben anzupassen

except Exception as e:
    st.error(f"Fehler beim Laden der Pipeline: {e}")
