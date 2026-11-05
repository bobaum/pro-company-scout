import streamlit as st
import pandas as pd
import re
import requests
import google.generativeai as genai
from supabase import create_client, Client
import PyPDF2

st.set_page_config(page_title="Personal Job Scout", layout="wide")
st.title("🎯 Personal Job Scout: Bo Baumann")

# --- APIs initialisieren ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_bereit = True
except Exception:
    api_bereit = False

try:
    places_api_key = st.secrets["PLACES_API_KEY"]
    places_bereit = True
except Exception:
    places_bereit = False

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

# --- Fünf personalisierte Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Datenbank", "📈 Meine Pipeline", "🧠 Skill-Gap Analyse", "👤 Mein Profil", "🌍 Live Company Scout"])

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
    
    if not api_bereit:
        st.error("⚠️ Gemini API-Schlüssel fehlt.")
    elif not db_bereit:
        st.error("⚠️ Datenbankverbindung fehlt.")
    else:
        profil_response = supabase.table("profil").select("*").eq("id", 1).execute()
        
        if not profil_response.data or not profil_response.data[0].get("lebenslauf"):
            st.warning("⚠️ Bitte hinterlege zuerst deinen Lebenslauf im Tab '👤 Mein Profil'.")
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
                        
                        Führe eine prägnante Skill-Gap-Analyse durch (Nutze Bulletpoints):
                        1. **Matching Hard- & Soft-Skills:** Was bringt der Bewerber perfekt für diese Rolle mit?
                        2. **Der Skill-Gap:** Welche Technologien/Anforderungen fehlen ihm noch?
                        3. **Handlungsempfehlung:** Wie kann er diese Lücke im Anschreiben strategisch kaschieren?
                        """
                        try:
                            antwort = model.generate_content(prompt).text
                            st.success("✅ Analyse abgeschlossen")
                            st.markdown(antwort)
                        except Exception as e:
                            st.error(f"Fehler bei der KI-Abfrage: {e}")

# ---------------------------------------------------------
# TAB 4: MEIN PROFIL
# ---------------------------------------------------------
with tab4:
    st.subheader("👤 Mein Profil & Lebenslauf")
    
    if db_bereit:
        profil_response = supabase.table("profil").select("*").eq("id", 1).execute()
        current_cv = profil_response.data[0].get("lebenslauf", "") if profil_response.data else ""
        current_skills = profil_response.data[0].get("skills", "") if profil_response.data else ""
        current_ziele = profil_response.data[0].get("ziele", "") if profil_response.data else ""
        
        uploaded_file = st.file_uploader("📄 Lebenslauf als PDF hochladen (optional)", type="pdf")
        if uploaded_file is not None:
            try:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                extracted_text = ""
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() + "\n"
                if extracted_text.strip():
                    current_cv = extracted_text
                    st.success("✅ PDF erfolgreich ausgelesen!")
            except Exception as e:
                st.error(f"Fehler beim Lesen des PDFs: {e}")
        
        with st.form("profil_form"):
            input_cv = st.text_area("📄 Dein Lebenslauf-Text:", value=current_cv, height=300)
            input_skills = st.text_input("🛠️ Zusätzliche Tech- & Soft-Skills:", value=current_skills, placeholder="z.B. Python, Streamlit, Supabase")
            input_ziele = st.text_input("🎯 Karriereziele:", value=current_ziele, placeholder="z.B. IT-Consulting Praktikum in Dublin")
            
            submitted = st.form_submit_button("💾 Profil in Cloud speichern")
            if submitted:
                profil_data = {"id": 1, "lebenslauf": input_cv, "skills": input_skills, "ziele": input_ziele}
                supabase.table("profil").upsert(profil_data).execute()
                st.success("✅ Dein Profil wurde erfolgreich aktualisiert!")

# ---------------------------------------------------------
# TAB 5: LIVE COMPANY SCOUT
# ---------------------------------------------------------
with tab5:
    st.subheader("🌍 Live Company Scout")
    st.write("Suche gezielt nach spannenden Unternehmen für Initiativbewerbungen und füge sie direkt deiner Pipeline hinzu.")
    
    if not places_bereit:
        st.error("⚠️ PLACES_API_KEY fehlt in den Streamlit Secrets.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            such_branche = st.text_input("Branche / Rolle:", placeholder="z.B. IT Consulting, PMO")
        with col2:
            such_ort = st.text_input("Stadt / Region:", placeholder="z.B. Dublin, Osnabrück")
            
        if st.button("🚀 Unternehmen suchen"):
            if such_branche and such_ort:
                with st.spinner(f"Suche nach '{such_branche}' in '{such_ort}'..."):
                    query = f"{such_branche} in {such_ort}"
                    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={places_api_key}"
                    
                    try:
                        url = "https://places.googleapis.com/v1/places:searchText"
                        
                        # Die neue API verlangt die Daten im Header (als "FieldMask" definieren wir, was wir wissen wollen)
                        headers = {
                            "Content-Type": "application/json",
                            "X-Goog-Api-Key": places_api_key,
                            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.id"
                        }
                        
                        # Der Suchbegriff wird als JSON-Payload gesendet
                        payload = {
                            "textQuery": f"{such_branche} in {such_ort}"
                        }
                        
                        response = requests.post(url, json=payload, headers=headers)
                        res = response.json()
                        
                        if response.status_code == 200:
                            places = res.get("places", [])
                            if places:
                                treffer = places[:15]
                                st.success(f"✅ {len(treffer)} Unternehmen gefunden!")
                                
                                for place in treffer:
                                    # Die neue API verschachtelt den Namen in 'displayName.text'
                                    name = place.get("displayName", {}).get("text", "Unbekannt")
                                    adresse = place.get("formattedAddress", "Keine Adresse hinterlegt")
                                    rating = place.get("rating", "Keine Bewertung")
                                    place_id = place.get("id")
                                    
                                    with st.expander(f"🏢 {name} (⭐ Rating: {rating})"):
                                        st.write(f"**Adresse:** {adresse}")
                                        
                                        if st.button(f"➕ {name} zur Pipeline hinzufügen", key=f"btn_{place_id}"):
                                            if db_bereit:
                                                new_entry = {"unternehmen": name, "rolle": f"Initiativ ({such_branche})", "status": "Neu", "notizen": adresse}
                                                supabase.table("pipeline").insert(new_entry).execute()
                                                st.success(f"Erfolgreich gespeichert! Du findest {name} jetzt in Tab 2.")
                                            else:
                                                st.error("Datenbankverbindung fehlt.")
                            else:
                                st.warning("Die Suche war erfolgreich, aber es wurden keine passenden Unternehmen in der Region gefunden.")
                        else:
                            st.error(f"Google API Fehler: {response.status_code}")
                            st.write(f"Details: {res.get('error', {}).get('message', 'Keine weiteren Infos')}")
                            
                    except Exception as e:
                        st.error(f"Systemfehler bei der Anfrage: {e}")
