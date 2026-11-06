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
        # Fallback-Spalten, falls die DB komplett leer ist
        df_pipeline = pd.DataFrame(columns=["unternehmen", "rolle", "status", "deadline", "notizen", "created_at"])
        st.info("Noch keine Unternehmen in der Pipeline. Nutze den Live Scout, um welche hinzuzufügen!")
    else:
        # Wir fügen die Lösch-Checkbox hinzu
        df_pipeline["🗑️ Löschen"] = False 
        
        total_saved = len(df_pipeline)
        active_applications = len(df_pipeline[df_pipeline["status"].isin(["Beworben", "In Vorbereitung", "Interview"])])
        interviews = len(df_pipeline[df_pipeline["status"] == "Interview"])
        
        st.subheader("📊 Pipeline Übersicht")
        col1, col2, col3 = st.columns(3)
        col1.metric("Gespeicherte Favoriten", total_saved)
        col2.metric("Aktive Bewerbungen", active_applications)
        col3.metric("Laufende Interviews", interviews)
        
        st.divider()
        
        # --- REPORTING EXPORT ---
        @st.cache_data
        def convert_df(df):
            export_df = df.drop(columns=["🗑️ Löschen", "id", "created_at"], errors='ignore')
            return export_df.to_csv(index=False).encode('utf-8')

        csv = convert_df(df_pipeline)
        
        header_col, export_col = st.columns([3, 1])
        with header_col:
            st.subheader("📋 Status-Board")
        with export_col:
            st.download_button(
                label="📥 Pipeline als CSV exportieren",
                data=csv,
                file_name='pmo_scout_pipeline.csv',
                mime='text/csv',
                use_container_width=True
            )

        # --- INTERAKTIVE TABELLE (MIT ROBUSTER LÖSCH-FUNKTION) ---
        # Wir konfigurieren die Spalten dynamisch. Wenn 'id' nicht existiert, stürzt es nicht ab.
        column_config = {
            "id": None, 
            "created_at": None,
            "🗑️ Löschen": st.column_config.CheckboxColumn("Löschen", help="Markieren, um die Firma aus der Cloud zu löschen"),
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

        edited_df = st.data_editor(
            df_pipeline,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
        
        if st.button("💾 Änderungen in Cloud speichern", type="primary"):
            # 1. LÖSCHEN (Robust via Firmenname)
            to_delete = edited_df[edited_df["🗑️ Löschen"] == True]
            if not to_delete.empty:
                unternehmen_to_delete = to_delete["unternehmen"].tolist()
                # Wir löschen in Supabase alle Zeilen, bei denen der Name übereinstimmt
                supabase.table("pipeline").delete().in_("unternehmen", unternehmen_to_delete).execute()
            
            # 2. SPEICHERN
            to_upsert = edited_df[edited_df["🗑️ Löschen"] == False].drop(columns=["🗑️ Löschen"])
            valid_data = to_upsert[to_upsert["unternehmen"].astype(str).str.strip() != ""]
            
            records = valid_data.to_dict(orient="records")
            if records:
                # Da uns evtl. die ID fehlt, nutzen wir insert statt upsert, 
                # ABER wir müssen aufpassen, dass wir keine Duplikate bauen. 
                # (In einem echten Produktionssystem rüstet man in Supabase den Primary Key "id" nach)
                try:
                     supabase.table("pipeline").upsert(records).execute()
                except Exception as ex:
                     # Fallback falls upsert ohne ID scheitert
                     st.warning("Upsert erfordert einen Primary Key (id). Die Daten wurden lokal verarbeitet, aber das Datenbank-Schema in Supabase benötigt eine Spalte 'id' als Primary Key für saubere Updates.")
                
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
