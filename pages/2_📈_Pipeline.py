import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Pipeline", page_icon="📈", layout="wide")
st.title("📈 Meine Bewerbungs-Pipeline")
st.markdown("Dein CRM-Board: Verwalte hier deine Favoriten und den Status deiner Initiativbewerbungen.")

# --- SESSION STATE FÜR ERFOLGSMELDUNG ---
if "save_success" not in st.session_state:
    st.session_state.save_success = False

if st.session_state.save_success:
    st.toast("✅ Änderungen erfolgreich in der Cloud gespeichert!", icon="💾")
    st.success("✅ Änderungen erfolgreich gespeichert!")
    st.session_state.save_success = False 

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
        df_pipeline = pd.DataFrame(columns=["id", "unternehmen", "rolle", "status", "deadline", "notizen", "created_at"])
        st.info("Noch keine Unternehmen in der Pipeline. Nutze den Live Scout, um welche hinzuzufügen!")
    else:
        total_saved = len(df_pipeline)
        active_applications = len(df_pipeline[df_pipeline["status"].isin(["Beworben", "In Vorbereitung", "Interview"])])
        interviews = len(df_pipeline[df_pipeline["status"] == "Interview"])
        
        st.subheader("📊 Pipeline Übersicht")
        col1, col2, col3 = st.columns(3)
        col1.metric("Gespeicherte Favoriten", total_saved)
        col2.metric("Aktive Bewerbungen", active_applications)
        col3.metric("Laufende Interviews", interviews)
        
        st.divider()
        
        # --- NEU: REPORTING EXPORT (PMO Feature) ---
        # Wir konvertieren den DataFrame in einen CSV-String (im UTF-8 Format)
        @st.cache_data
        def convert_df(df):
            # Index weglassen, als CSV formatieren
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(df_pipeline)
        
        # --- KOPFZEILE MIT BUTTONS ---
        header_col, export_col = st.columns([3, 1])
        with header_col:
            st.subheader("📋 Status-Board")
        with export_col:
            # Download-Button mit dem konvertierten CSV
            st.download_button(
                label="📥 Pipeline als CSV exportieren",
                data=csv,
                file_name='pmo_scout_pipeline.csv',
                mime='text/csv',
                use_container_width=True
            )

        # --- INTERAKTIVE TABELLE ---
        edited_df = st.data_editor(
            df_pipeline,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, 
                "created_at": None,
                "unternehmen": st.column_config.TextColumn("Unternehmen", disabled=True), 
                "rolle": st.column_config.TextColumn("Rolle / Bereich"),
                "status": st.column_config.SelectboxColumn(
                    "Aktueller Status",
                    options=["Neu", "In Vorbereitung", "Beworben", "Interview", "Angebot", "Abgesagt", "On Hold"],
                    required=True
                ),
                "deadline": st.column_config.DateColumn("Deadline"),
                "notizen": st.column_config.TextColumn("Notizen & Adresse")
            }
        )
        
        if st.button("💾 Änderungen in Cloud speichern", type="primary"):
            valid_data = edited_df[edited_df["unternehmen"].astype(str).str.strip() != ""]
            records = valid_data.to_dict(orient="records")
            if records:
                supabase.table("pipeline").upsert(records).execute()
                st.session_state.save_success = True
                st.rerun()

        st.divider()
        
        # --- KI-ANALYSE AUS DER PIPELINE STARTEN ---
        st.subheader("🤖 KI-Analyse für Favoriten")
        unternehmen_liste = df_pipeline["unternehmen"].tolist()
        
        col_auswahl, col_btn = st.columns([3, 1])
        with col_auswahl:
            selected_company = st.selectbox("Wähle ein Unternehmen aus deiner Pipeline:", unternehmen_liste)
        with col_btn:
            st.write("") 
            st.write("")
            if st.button("🚀 KI-Match prüfen"):
                details = df_pipeline[df_pipeline["unternehmen"] == selected_company]["notizen"].iloc[0]
                
                st.session_state.analyze_company_name = selected_company
                st.session_state.analyze_company_details = details if details else "Aus Pipeline übernommen"
                st.switch_page("pages/3_🧠_KI_Analyse.py")

except Exception as e:
    st.error(f"Fehler beim Laden der Pipeline: {e}")
