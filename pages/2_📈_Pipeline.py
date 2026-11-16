import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Bewerbungs-Pipeline", page_icon="📈", layout="wide")
st.title("📈 Bewerbungs-Pipeline & CRM")
st.markdown("Verwalte deine Kontakte, Status und Notizen zu deinen Wunsch-Arbeitgebern.")

# --- DATENBANK ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = get_db()

if not supabase:
    st.error("⚠️ Supabase-Verbindung fehlgeschlagen. Prüfe deine Secrets.")
    st.stop()

# --- DATEN LADEN ---
def load_pipeline():
    try:
        res = supabase.table("pipeline").select("*").execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame(columns=["id", "unternehmen", "rolle", "ansprechpartner", "status", "notizen"])
    except Exception as e:
        st.error(f"Fehler beim Laden der Pipeline: {e}")
        return pd.DataFrame(columns=["id", "unternehmen", "rolle", "ansprechpartner", "status", "notizen"])

df_pipeline = load_pipeline()

# --- KPIs ANZEIGEN ---
if not df_pipeline.empty:
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Gespeicherte Unternehmen", len(df_pipeline))
    active_count = len(df_pipeline[df_pipeline["status"].isin(["In Vorbereitung", "Beworben", "Interview"])])
    kpi2.metric("Aktive Prozesse", active_count)
    interview_count = len(df_pipeline[df_pipeline["status"] == "Interview"])
    kpi3.metric("Interviews / Gespräche", interview_count)
    st.divider()

# --- DATEN BEARBEITEN (CRM BOARD) ---
if df_pipeline.empty:
    st.info("Noch keine Unternehmen in der Pipeline. Nutze den Live Scout oder die KI-Analyse, um Firmen hinzuzufügen!")
else:
    st.subheader("Übersicht & Status-Pflege")
    st.markdown("Du kannst den Status direkt in der Tabelle anpassen oder Zeilen bearbeiten.")

    status_options = ["Neu", "In Vorbereitung", "Beworben", "Interview", "Absage", "Angebot"]

    edited_df = st.data_editor(
        df_pipeline,
        num_rows="dynamic",
        use_container_width=True,
        key="pipeline_editor",
        column_config={
            "id": None,  # ID-Spalte für den Nutzer ausblenden, aber intern behalten
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=status_options,
                required=True
            )
        }
    )

    # --- SPEICHER-BUTTON FÜR ÄNDERUNGEN ---
    if st.button("Änderungen in Cloud speichern", type="primary"):
        try:
            # Konvertiere den editierten DataFrame zurück in ein Dictionary-Format für Supabase
            records = edited_df.to_dict(orient="records")
            
            # Upsert in die Supabase Pipeline-Tabelle
            supabase.table("pipeline").upsert(records).execute()
            st.success("Pipeline erfolgreich aktualisiert!")
            st.toast("Daten in Supabase gespeichert", icon="💾")
            st.rerun()
        except Exception as ex:
            # Zeigt den echten Systemfehler exakt an statt ihn zu verschlucken[cite: 4]
            st.error(f"Fehler beim Cloud-Update: {ex}")

# --- CSV EXPORT ---
if not df_pipeline.empty:
    st.divider()
    csv = df_pipeline.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Pipeline als CSV herunterladen",
        data=csv,
        file_name='bewerbungs_pipeline.csv',
        mime='text/csv',
    )
