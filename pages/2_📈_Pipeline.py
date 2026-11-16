import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Bewerbungs-Pipeline", page_icon="📈", layout="wide")
st.title("📈 Bewerbungs-Pipeline & CRM")
st.markdown("Verwalte deine Kontakte, Status und Notizen zu deinen Wunsch-Arbeitgebern auf einen Blick.")

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
        return pd.DataFrame(columns=["id", "unternehmen", "rolle", "ansprechpartner", "status", "deadline", "notizen"])
    except Exception as e:
        st.error(f"Fehler beim Laden der Pipeline: {e}")
        return pd.DataFrame(columns=["id", "unternehmen", "rolle", "ansprechpartner", "status", "deadline", "notizen"])

df_pipeline = load_pipeline()

# --- ERWEITERTE KPI-METRIKEN ---
if not df_pipeline.empty:
    col1, col2, col3, col4 = st.columns(4)
    total_companies = len(df_pipeline)
    active_count = len(df_pipeline[df_pipeline["status"].isin(["⏳ In Vorbereitung", "In Vorbereitung", "📤 Beworben", "Beworben", "🎯 Interview", "Interview"])])
    interview_count = len(df_pipeline[df_pipeline["status"].isin(["🎯 Interview", "Interview"])])
    offer_count = len(df_pipeline[df_pipeline["status"].isin(["🤝 Angebot", "Angebot"])])

    col1.metric("📁 Gespeicherte Firmen", total_companies)
    col2.metric("⚡ Aktive Prozesse", active_count)
    col3.metric("🎯 Interviews", interview_count)
    col4.metric("🤝 Angebote", offer_count)
    st.divider()

# --- DATEN BEARBEITEN (CRM BOARD) MIT EMOJI-STATUS ---
if df_pipeline.empty:
    st.info("Noch keine Unternehmen in der Pipeline. Nutze den Live Scout oder die KI-Analyse, um Firmen hinzuzufügen!")
else:
    st.subheader("📋 CRM-Übersicht & Status-Pflege")
    st.markdown("Passe den Status direkt über das Dropdown an oder ergänze Details.")

    status_options = [
        "🆕 Neu",
        "⏳ In Vorbereitung",
        "📤 Beworben",
        "🎯 Interview",
        "❌ Absage",
        "🤝 Angebot"
    ]

    # Falls alte Status-Werte in der DB stehen, sauber mappen
    if "status" in df_pipeline.columns:
        mapping = {
            "Neu": "🆕 Neu",
            "In Vorbereitung": "⏳ In Vorbereitung",
            "Beworben": "📤 Beworben",
            "Interview": "🎯 Interview",
            "Absage": "❌ Absage",
            "Angebot": "🤝 Angebot"
        }
        df_pipeline["status"] = df_pipeline["status"].replace(mapping)

    edited_df = st.data_editor(
        df_pipeline,
        num_rows="dynamic",
        use_container_width=True,
        key="pipeline_editor",
        column_config={
            "id": None,  # ID-Spalte für den Nutzer ausblenden
            "unternehmen": st.column_config.TextColumn("🏢 Unternehmen", required=True),
            "rolle": st.column_config.TextColumn("💼 Angestrebte Rolle"),
            "status": st.column_config.SelectboxColumn(
                "📌 Status",
                options=status_options,
                required=True
            ),
            "deadline": st.column_config.TextColumn("📅 Deadline"),
            "ansprechpartner": st.column_config.TextColumn("👤 Ansprechpartner"),
            "notizen": st.column_config.TextColumn("📝 Notizen / Key-Insights")
        }
    )

    # --- SPEICHER-BUTTON ---
    col_save, _ = st.columns([1, 3])
    with col_save:
        if st.button("💾 Änderungen in Cloud speichern", type="primary", use_container_width=True):
            try:
                records = edited_df.to_dict(orient="records")
                supabase.table("pipeline").upsert(records).execute()
                st.success("Pipeline erfolgreich aktualisiert!")
                st.toast("Daten in Supabase gespeichert", icon="💾")
                st.rerun()
            except Exception as ex:
                st.error(f"Fehler beim Cloud-Update: {ex}")

# --- VISUELLE STATUS-FOKUS ANSICHT (KARTEN) ---
if not df_pipeline.empty:
    st.divider()
    st.subheader("🔍 Status-Fokus (Kompaktansicht)")
    
    tabs = st.tabs(["📁 Alle", "⏳ In Vorbereitung", "📤 Beworben", "🎯 Interview", "🤝 Angebot"])
    
    status_filter_map = {
        "📁 Alle": None,
        "⏳ In Vorbereitung": "⏳ In Vorbereitung",
        "📤 Beworben": "📤 Beworben",
        "🎯 Interview": "🎯 Interview",
        "🤝 Angebot": "🤝 Angebot"
    }
    
    for i, (tab_name, filter_val) in enumerate(status_filter_map.items()):
        with tabs[i]:
            if filter_val is None:
                subset = df_pipeline
            else:
                subset = df_pipeline[df_pipeline["status"] == filter_val]
                
            if subset.empty:
                st.caption("Keine Einträge in dieser Kategorie.")
            else:
                cols = st.columns(min(len(subset), 3))
                for idx, row in enumerate(subset.iterrows()):
                    data = row[1]
                    with cols[idx % 3]:
                        with st.container(border=True):
                            st.markdown(f"**🏢 {data.get('unternehmen', 'Unbekannt')}**")
                            st.caption(f"💼 {data.get('rolle', 'Keine Rolle angegeben')}")
                            st.markdown(f"Status: `{data.get('status', 'Neu')}`")
                            contact = data.get('ansprechpartner')
                            if contact and str(contact).lower() != "none" and str(contact).strip() != "":
                                st.write(f"👤 {contact}")

# --- CSV EXPORT ---
if not df_pipeline.empty:
    st.divider()
    csv = df_pipeline.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Pipeline als CSV herunterladen",
        data=csv,
        file_name='bewerbungs_pipeline.csv',
        mime='text/css', # CSV mime fix
    )
