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

# --- Vier personalisierte Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Datenbank", "📈 Meine Pipeline", "🧠 Skill-Gap Analyse", "👤 Mein Profil"])

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
# TAB 2: BEWERBUNGS-PIPELINE
# ---------------------------------------------------------
with tab2:
    st.subheader("📈 Tracking: Aktuelle Bewerbungen")
    if not db_bereit:
        st.error("⚠️ Datenbankverbindung fehlt.")
    else:
        try:
            response = supabase.table("pipeline").select("*").execute()
            df_pipeline = pd.DataFrame(response.data)
            if df_pipeline.empty:
                df_pipeline = pd.DataFrame(columns=["unternehmen", "rolle", "status", "deadline", "notizen"])
            
            edited_df = st.data_editor(
                df_pipeline, 
                num_rows="dynamic",
                width="stretch",
                column_config={
                    "status": st.column_config.SelectboxColumn("Status", options=["Neu", "In Vorbereitung", "Beworben", "Interview", "Angebot", "Abgesagt"])
                }
            )
            
            if st.button("💾 Änderungen in Pipeline speichern"):
                valid_data = edited_df[edited_df["unternehmen"].astype(str).str.strip() != ""]
                records = valid_data.to_dict(orient="records")
                if records:
                    supabase.table("pipeline").upsert(records).execute()
                    st.success("✅ Pipeline aktualisiert!")
        except Exception as e:
            st.error(f"Fehler: {e}")

# ---------------------------------------------------------
# TAB 3: SKILL-GAP & BEWERBUNGS-HELFER
# ---------------------------------------------------------
with tab3:
    st.subheader("🧠 KI Skill-Gap Analyse")
    st.write("Vergleicht dein Profil dynamisch mit einer Stellenausschreibung.")
    
    if not api_bereit:
        st.error("⚠️ Gemini API-Schlüssel fehlt.")
    elif not db_bereit:
        st.error("⚠️ Datenbankverbindung fehlt.")
    else:
        # Profil live aus der Datenbank laden
        profil_response = supabase.table("profil").select("*").eq("id", 1).execute()
        
        if not profil_response.data or not profil_response.data[0].get("lebenslauf"):
            st.warning("⚠️ Bitte hinterlege zuerst deinen Lebenslauf im Tab '👤 Mein Profil', damit die KI dich analysieren kann.")
        else:
            mein_profil = profil_response.data[0]
            
            ziel_unternehmen = st.text_input("Ziel-Unternehmen:", placeholder="z.B. KPMG")
            stellen_details = st.text_area("Stichpunkte aus der Stellenanzeige:", height=100)
            
            if st.button("Skill-Gap analysieren"):
                if not ziel_unternehmen:
                    st.warning("Bitte gib ein Ziel-Unternehmen ein.")
                else:
                    with st.spinner("Gemini analysiert dein Profil..."):
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = f"""
                        Du bist ein technischer Karriere-Scout.
                        
                        Hier ist der detaillierte Lebenslauf und das Profil des Bewerbers:
                        Lebenslauf: {mein_profil.get('lebenslauf', 'Nicht angegeben')}
                        Zusätzliche Skills: {mein_profil.get('skills', 'Nicht angegeben')}
                        Karriereziele: {mein_profil.get('ziele', 'Nicht angegeben')}
                        
                        Ziel-Unternehmen & Rolle: '{ziel_unternehmen}'
                        Details zur Stelle: '{stellen_details}'
                        
                        Führe eine prägnante Skill-Gap-Analyse durch. Strukturiere die Antwort in diese 3 Bereiche (nutze Bulletpoints):
                        1. **Matching Hard- & Soft-Skills:** Was bringt der Bewerber durch seinen Lebenslauf bereits perfekt für diese Rolle mit?
                        2. **Der Skill-Gap:** Welche Technologien oder Anforderungen fehlen ihm für diese konkrete Rolle wahrscheinlich noch?
                        3. **Handlungsempfehlung:** Wie kann er diese Lücke im Anschreiben strategisch kaschieren oder durch seine bestehenden Erfahrungen ausgleichen?
                        """
                        
                        try:
                            antwort = model.generate_content(prompt).text
                            st.success("✅ Analyse abgeschlossen")
                            st.markdown(antwort)
                        except Exception as e:
                            st.error(f"Fehler bei der KI-Abfrage: {e}")

# ---------------------------------------------------------
# TAB 4: MEIN PROFIL (Dynamischer Lebenslauf)
# ---------------------------------------------------------
with tab4:
    st.subheader("👤 Mein Profil & Lebenslauf")
    st.write("Hinterlege hier deinen Harvard-Lebenslauf und deine Skills. Die KI in Tab 3 nutzt diese Daten für alle Analysen.")
    
    if db_bereit:
        # Aktuelles Profil laden, falls vorhanden (Wir nutzen id=1 als festen Datensatz für dich)
        profil_response = supabase.table("profil").select("*").eq("id", 1).execute()
        current_cv = ""
        current_skills = ""
        current_ziele = ""
        
        if profil_response.data:
            current_cv = profil_response.data[0].get("lebenslauf", "")
            current_skills = profil_response.data[0].get("skills", "")
            current_ziele = profil_response.data[0].get("ziele", "")
            
        with st.form("profil_form"):
            input_cv = st.text_area("📄 Dein Lebenslauf (Kopiere hier deinen Harvard-CV rein):", value=current_cv, height=300)
            input_skills = st.text_input("🛠️ Zusätzliche Tech- & Soft-Skills (Kommasepariert):", value=current_skills, placeholder="z.B. Python, Streamlit, Supabase, Hardware-Setup")
            input_ziele = st.text_input("🎯 Karriereziele (Für die KI als Kontext):", value=current_ziele, placeholder="z.B. IT-Consulting Praktikum in Dublin")
            
            submitted = st.form_submit_button("💾 Profil speichern")
            if submitted:
                # Wir überschreiben immer den Datensatz mit id=1
                profil_data = {
                    "id": 1,
                    "lebenslauf": input_cv,
                    "skills": input_skills,
                    "ziele": input_ziele
                }
                supabase.table("profil").upsert(profil_data).execute()
                st.success("Dein Profil wurde erfolgreich in der Cloud aktualisiert! Tab 3 nutzt ab sofort diese neuen Daten.")
