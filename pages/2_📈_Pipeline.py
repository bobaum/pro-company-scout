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
        df_pipeline = pd.DataFrame(columns=["unternehmen", "rolle", "status", "deadline", "notizen", "created_at"])
        st.info("Noch keine Unternehmen in der Pipeline. Nutze den Live Scout, um welche hinzuzufügen!")
    else:
        # VISUAL HYGIENE: Wir konvertieren alte Text-Stati in das neue Ampelsystem
        status_mapping = {
            "Neu": "🆕 Neu", 
            "In Vorbereitung": "🟡 In Vorbereitung", 
            "Beworben": "📤 Beworben", 
            "Interview": "🟢 Interview", 
            "Angebot": "🎉 Angebot", 
            "Abgesagt": "🔴 Abgesagt", 
            "On Hold": "⏸️ On Hold"
        }
        # Wendet das Mapping nur an, wenn der alte Status gefunden wird (schützt vor doppelter Ausführung)
        df_pipeline["status"] = df_pipeline["status"].apply(lambda x: status_mapping.get(x, x))
        
        df_pipeline["🗑️ Löschen"] = False 
        
        total_saved = len(df_pipeline)
        active_applications = len(df_pipeline[df_pipeline["status"].isin(["📤 Beworben", "🟡 In Vorbereitung", "🟢 Interview"])])
        interviews = len(df_pipeline[df_pipeline["status"] == "🟢 Interview"])
        
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

        # --- INTERAKTIVE TABELLE ---
        column_config = {
            "id": None, 
            "created_at": None,
            "🗑️ Löschen": st.column_config.CheckboxColumn("Löschen", help="Markieren, um die Firma aus der Cloud zu löschen"),
            "unternehmen": st.column_config.TextColumn("Unternehmen", disabled=True), 
            "rolle": st.column_config.TextColumn("Rolle / Bereich"),
            "status": st.column_config.SelectboxColumn(
                "Ampel-Status",
                options=list(status_mapping.values()), # Nutzt die neuen Emoji-Werte
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
            to_delete = edited_df[edited_df["🗑️ Löschen"] == True]
            if not to_delete.empty:
                unternehmen_to_delete = to_delete["unternehmen"].tolist()
                supabase.table("pipeline").delete().in_("unternehmen", unternehmen_to_delete).execute()
            
            to_upsert = edited_df[edited_df["🗑️ Löschen"] == False].drop(columns=["🗑️ Löschen"])
            valid_data = to_upsert[to_upsert["unternehmen"].astype(str).str.strip() != ""]
            
            records = valid_data.to_dict(orient="records")
            if records:
                try:
                     supabase.table("pipeline").upsert(records).execute()
                except Exception as ex:
                     st.warning("Fehler beim Cloud-Update.")
                
            st.session_state.save_success = True
            st.rerun()

        st.divider()
        
        # --- OFFLINE FEATURE: TEMPLATE GENERATOR ---
        st.subheader("📝 Anschreiben-Generator (Initiativbewerbung)")
        unternehmen_liste = df_pipeline["unternehmen"].tolist()
        
        if unternehmen_liste:
            selected_company_letter = st.selectbox("Zielunternehmen für das Anschreiben auswählen:", unternehmen_liste, key="letter_select")
            
            if st.button("⚙️ Textgerüst generieren"):
                # Unternehmensspezifische Daten abgreifen
                company_role = df_pipeline[df_pipeline["unternehmen"] == selected_company_letter]["rolle"].iloc[0]
                if not company_role or str(company_role).strip() == "":
                    company_role = "IT-Consulting und Projektmanagement"

                template_text = f"""Sehr geehrte Damen und Herren,

auf der Suche nach einem dynamischen und innovationsgetriebenen Umfeld im Bereich {company_role} bin ich auf {selected_company_letter} aufmerksam geworden. Mit meinem klaren Fokus auf die Schnittstelle zwischen Technologie und Wirtschaftsorganisation möchte ich mein Profil proaktiv in Ihr Team einbringen.

Als Student der Wirtschaftsinformatik (B.Sc.) an der Hochschule Osnabrück verfüge ich über ein starkes analytisches Fundament. Parallel dazu verantworte ich in meiner aktuellen Praxisrolle das operative IT-Infrastrukturmanagement. Diese Kombination aus strategischem Studium und handfester IT-Operations-Erfahrung ermöglicht es mir, technische Anforderungen nicht nur zu verstehen, sondern zielgerichtet in funktionierende Geschäftsprozesse zu übersetzen.

Mich reizt besonders die Möglichkeit, bei {selected_company_letter} PMO-Strukturen zu unterstützen, IT-Projekte ganzheitlich zu begleiten und mich langfristig im Consulting-Umfeld zu etablieren. Ich arbeite strukturiert, übernehme gerne Verantwortung und behalte auch bei komplexen Rollouts den systemischen Überblick.

Gerne überzeuge ich Sie in einem persönlichen Gespräch von meiner Motivation und meiner pragmatischen Hands-on-Mentalität. 

Mit freundlichen Grüßen,

Bo Baumann"""
                
                st.info("Dein personalisiertes Grundgerüst. Kopiere den Text und passe ihn für die finale Bewerbung leicht an.")
                st.text_area("Generiertes Anschreiben:", value=template_text, height=350)
        else:
            st.write("Füge Unternehmen zur Pipeline hinzu, um Anschreiben zu generieren.")

except Exception as e:
    st.error(f"Fehler beim Laden der Pipeline: {e}")
