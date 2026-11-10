import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Pipeline", page_icon="📈", layout="wide")

st.title("Meine Bewerbungs Pipeline")
st.markdown("Dein CRM Board: Verwalte hier deine Favoriten und den Status deiner Initiativbewerbungen.")

# --- DATENBANK ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = get_db()

if not supabase:
    st.error("Keine Verbindung zur Datenbank möglich. Bitte Secrets prüfen.")
    st.stop()

# --- DATEN LADEN ---
def load_data():
    try:
        res = supabase.table("pipeline").select("*").execute()
        if res.data:
            return pd.DataFrame(res.data)
        else:
            return pd.DataFrame(columns=["id", "unternehmen", "rolle", "status", "ansprechpartner", "deadline", "notizen"])
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return pd.DataFrame()

df = load_data()

# --- KPI DASHBOARD ---
if not df.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Gespeicherte Favoriten", len(df))
    with col2:
        aktive = len(df[df["status"] != "Abgesagt"])
        st.metric("Aktive Bewerbungen", aktive)
    with col3:
        interviews = len(df[df["status"] == "Interview"])
        st.metric("Laufende Interviews", interviews)

st.divider()

# --- NEUEN LEAD MANUELL HINZUFÜGEN ---
with st.expander("Neues Unternehmen manuell hinzufügen"):
    with st.form("new_lead_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            neu_unternehmen = st.text_input("Unternehmen *")
            neu_rolle = st.text_input("Rolle oder Bereich (z.B. PMO)")
            neu_status = st.selectbox("Status", ["Neu", "In Vorbereitung", "Bewerbung raus", "Interview", "Abgesagt", "Zusage"])
        with col_b:
            neu_ansprechpartner = st.text_input("Ansprechpartner (HR / Fachbereich)")
            neu_deadline = st.date_input("Deadline oder Wiedervorlage", value=None)
            neu_notizen = st.text_area("Notizen", height=100)
        
        submitted = st.form_submit_button("Speichern", type="primary", width="stretch")
        if submitted:
            if neu_unternehmen:
                neu_daten = {
                    "unternehmen": neu_unternehmen,
                    "rolle": neu_rolle,
                    "status": neu_status,
                    "ansprechpartner": neu_ansprechpartner,
                    "deadline": str(neu_deadline) if neu_deadline else None,
                    "notizen": neu_notizen
                }
                supabase.table("pipeline").insert(neu_daten).execute()
                st.toast(f"{neu_unternehmen} erfolgreich gespeichert!")
                st.rerun()
            else:
                st.warning("Unternehmensname ist ein Pflichtfeld.")

# --- STATUS BOARD (CRM TABELLE) ---
st.subheader("Status Board")

if not df.empty:
    # Sortieren der Spalten für eine saubere Ansicht
    anzeige_df = df[["id", "unternehmen", "rolle", "ansprechpartner", "status", "deadline", "notizen"]].copy()
    
    # Interaktiver Data Editor
    edited_df = st.data_editor(
        anzeige_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": None, # ID verstecken
            "unternehmen": st.column_config.TextColumn("Unternehmen", required=True),
            "rolle": st.column_config.TextColumn("Rolle / Bereich"),
            "ansprechpartner": st.column_config.TextColumn("Ansprechpartner"),
            "status": st.column_config.SelectboxColumn("Status", options=["Neu", "In Vorbereitung", "Bewerbung raus", "Interview", "Abgesagt", "Zusage"], required=True),
            "deadline": st.column_config.DateColumn("Wiedervorlage"),
            "notizen": st.column_config.TextColumn("Notizen")
        },
        num_rows="dynamic",
        key="pipeline_editor"
    )

    if st.button("Änderungen in Cloud speichern", type="primary"):
        # Gelöschte Reihen aus der Datenbank entfernen
        if st.session_state.pipeline_editor["deleted_rows"]:
            for row_idx in st.session_state.pipeline_editor["deleted_rows"]:
                del_id = anzeige_df.iloc[row_idx]["id"]
                supabase.table("pipeline").delete().eq("id", del_id).execute()
        
        # Geänderte Reihen aktualisieren
        if st.session_state.pipeline_editor["edited_rows"]:
            for row_idx, changes in st.session_state.pipeline_editor["edited_rows"].items():
                edit_id = anzeige_df.iloc[row_idx]["id"]
                supabase.table("pipeline").update(changes).eq("id", edit_id).execute()
        
        # Neue Reihen hinzufügen
        if st.session_state.pipeline_editor["added_rows"]:
            for new_row in st.session_state.pipeline_editor["added_rows"]:
                supabase.table("pipeline").insert(new_row).execute()
                
        st.success("Datenbank erfolgreich synchronisiert!")
        st.rerun()
else:
    st.info("Deine Pipeline ist noch leer. Füge über den Scout oder das Formular oben Unternehmen hinzu.")
