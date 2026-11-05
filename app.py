import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
from supabase import create_client, Client

st.set_page_config(page_title="Personal Job Scout", layout="wide")
st.title("🎯 Personal Job Scout: Bo Baumann")

# --- APIs initialisieren ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_bereit = True
except Exception:
    api_bereit = False

try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
    db_bereit = True
except Exception:
    db_bereit = False

# --- Daten laden für Tab 1 ---
@st.cache_data
def load_and_clean_data():
    try:
        df = pd.read_excel("osnabrueck_matched.xlsx")
    except Exception as e:
        return pd.DataFrame()

    def clean_rating(val):
        val = str(val).lower()
        if "sehr hoch" in val or "5/5" in val: return 5
        if "hoch" in val or "4/5" in val: return 4
        if "mittel" in val or "3/5" in val: return 3
        if "gering" in val or "2/5" in val: return 2
        if "sehr gering" in val or "1/5" in val: return 1
        nums = re.findall(r'\d+', val)
        return int(nums[0]) if nums else 3

    def clean_chancen(val):
        val = str(val).lower()
        if "ja" in val or "werkstudent" in val or "hoch" in val: return "Ja"
        if "nein" in val or "gering" in val: return "Nein"
        return "Initiativ"

    if not df.empty:
        df["Match-Rating"] = df["Match-Rating"].apply(clean_rating)
        df["Einstiegschancen"] = df["Einstiegschancen"].apply(clean_chancen)
    return df

df = load_and_clean_data()

# --- Drei personalisierte Tabs ---
tab1, tab2, tab3 = st.tabs(["📊 Datenbank", "📈 Meine Pipeline", "🧠 Skill-Gap Analyse"])

# ---------------------------------------------------------
# TAB 1: DATENBANK
# ---------------------------------------------------------
with tab1:
    if not df.empty:
        st.markdown("Deine bereinigte Übersicht für PMO, IT-Projektkoordination und Consulting.")
        rating_auswahl = st.slider("Min. Match-Rating (Sterne):", 1, 5, 3)
        df_filtered = df[df["Match-Rating"] >= rating_auswahl]
        
        cols_to_drop = [col for col in ["Begründung", "Adresse"] if col in df_filtered.columns]
        st.dataframe(df_filtered.drop(columns=cols_to_drop), width='stretch', hide_index=True)
    else:
        st.warning("Bitte lade die Datei 'osnabrueck_matched.xlsx' hoch.")

# ---------------------------------------------------------
# TAB 2: BEWERBUNGS-PIPELINE (Supabase)
# ---------------------------------------------------------
with tab2:
    st.subheader("📈 Tracking: Aktuelle Bewerbungen")
    st.write("Verwalte hier deine offenen Kontakte. Die Daten liegen sicher in deiner Supabase Cloud-Datenbank.")
    
    if not db_bereit:
        st.error("⚠️ Datenbankverbindung fehlt. Prüfe die Supabase Secrets in Streamlit.")
    else:
        try:
            # 1. Daten live aus Supabase abrufen
            response = supabase.table("pipeline").select("*").execute()
            df_pipeline = pd.DataFrame(response.data)
            
            # Falls die Tabelle noch komplett leer ist
            if df_pipeline.empty:
                df_pipeline = pd.DataFrame(columns=["unternehmen", "rolle", "status", "deadline", "notizen"])
            
            # 2. Interaktive Tabelle anzeigen (width statt use_container_width)
            edited_df = st.data_editor(
                df_pipeline, 
                num_rows="dynamic",
                width="stretch",
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Neu", "In Vorbereitung", "Beworben", "Interview", "Angebot", "Abgesagt"]
                    )
                }
            )
            
            # 3. Speichern-Button
            if st.button("💾 Änderungen in Cloud speichern"):
                valid_data = edited_df[edited_df["unternehmen"].astype(str).str.strip() != ""]
                records = valid_data.to_dict(orient="records")
                
                if records:
                    supabase.table("pipeline").upsert(records).execute()
                    st.success("✅ Pipeline erfolgreich synchronisiert!")
                else:
                    st.warning("Keine gültigen Daten zum Speichern gefunden.")
                    
        except Exception as e:
            st.error(f"Fehler bei der Datenbank-Aktion: {e}")

# ---------------------------------------------------------
# TAB 3: SKILL-GAP & BEWERBUNGS-HELFER
# ---------------------------------------------------------
with tab3:
    st.subheader("🧠 KI Skill-Gap Analyse")
    st.write("Vergleicht dein Profil mit den Anforderungen einer spezifischen Firma oder Stellenausschreibung.")
    
    if not api_bereit:
        st.error("⚠️ Gemini API-Schlüssel fehlt.")
        
    ziel_unternehmen = st.text_input("Für welches Unternehmen möchtest du die Analyse starten?", placeholder="z.B. KPMG - Praktikum IT Consulting")
    stellen_details = st.text_area("Optional: Füge hier Stichpunkte aus der Stellenanzeige ein:", height=100)
    
    if st.button("Skill-Gap analysieren"):
        if not ziel_unternehmen:
            st.warning("Bitte gib ein Ziel-Unternehmen ein.")
        else:
            with st.spinner("Gemini analysiert dein Profil..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                Du bist ein technischer Karriere-Scout.
                
                Profil des Bewerbers (Bo Baumann): 
                - Studium: Bachelor Wirtschaftsinformatik (3. Semester)
                - Praktische Erfahrung: Minijob im internen IT-Support (Infrastruktur-Administration, Hardware-Konfiguration)
                - Ziel: Praktikum/Werkstudent im Bereich IT-Consulting, PMO oder Cloud Services (Perspektive: späteres Auslandspraktikum in Dublin).
                
                Ziel-Unternehmen & Rolle: '{ziel_unternehmen}'
                Details zur Stelle: '{stellen_details}'
                
                Führe eine prägnante Skill-Gap-Analyse durch. Strukturiere die Antwort in diese 3 Bereiche (nutze Bulletpoints):
                1. **Matching Hard- & Soft-Skills:** Was bringt Bo durch sein Studium und den IT-Support bereits perfekt für diese Rolle mit?
                2. **Der Skill-Gap:** Welche Technologien oder Soft-Skills fehlen ihm für diese konkrete Rolle wahrscheinlich noch?
                3. **Handlungsempfehlung:** Wie kann er diese Lücke im Anschreiben strategisch kaschieren oder in den nächsten Wochen gezielt schließen?
                """
                
                try:
                    antwort = model.generate_content(prompt).text
                    st.success("✅ Analyse abgeschlossen")
                    st.markdown(antwort)
                except Exception as e:
                    st.error(f"Fehler bei der KI-Abfrage: {e}")
