import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
import time

st.set_page_config(page_title="Company Scout Osnabrück", layout="wide")
st.title("🎯 Company Scout Osnabrück")

# --- API Key aus den Streamlit Secrets laden ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_bereit = True
except Exception:
    api_bereit = False

@st.cache_data
def load_and_clean_data():
    df = pd.read_excel("osnabrueck_matched.xlsx")

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

    def clean_kategorie(val):
        val = str(val).lower()
        if "consulting" in val or "beratung" in val: return "Consulting & Beratung"
        if "it" in val or "software" in val or "system" in val or "cloud" in val: return "IT & Tech"
        if "logistik" in val or "transport" in val or "spedition" in val: return "Logistik & SCM"
        if "industrie" in val or "produktion" in val or "fertigung" in val: return "Industrie"
        if "holding" in val or "finanz" in val: return "Finance & Holding"
        return "Wirtschaft & Sonstiges"

    df["Match-Rating"] = df["Match-Rating"].apply(clean_rating)
    df["Einstiegschancen"] = df["Einstiegschancen"].apply(clean_chancen)
    df["Kategorie"] = df["Kategorie"].apply(clean_kategorie)
    return df

try:
    df = load_and_clean_data()
    
    # --- UI in zwei Tabs aufteilen ---
    tab1, tab2 = st.tabs(["📊 Datenbank (PMO & IT)", "🤖 Neue Live-Analyse (SaaS)"])
    
    with tab1:
        st.markdown("Deine bereinigte Übersicht für PMO, IT-Projektkoordination und Consulting.")
        
        st.sidebar.header("⚙️ Filter (für Tab 1)")
        kat_auswahl = st.sidebar.multiselect("Große Branchen:", df["Kategorie"].unique(), default=df["Kategorie"].unique())
        such_auswahl = st.sidebar.multiselect("Suchbegriff (Google):", df["Suchbegriff"].unique(), default=df["Suchbegriff"].unique())
        rating_auswahl = st.sidebar.slider("Min. Match-Rating (Sterne):", 1, 5, 3)
        chancen_auswahl = st.sidebar.multiselect("Einstiegschancen:", df["Einstiegschancen"].unique(), default=["Ja", "Initiativ"])
        
        df_filtered = df[
            (df["Kategorie"].isin(kat_auswahl)) & 
            (df["Suchbegriff"].isin(such_auswahl)) &
            (df["Match-Rating"] >= rating_auswahl) &
            (df["Einstiegschancen"].isin(chancen_auswahl))
        ]
        
        search = st.text_input("🔍 Freitext-Suche (Namen, Begründung):")
        if search:
            df_filtered = df_filtered[df_filtered.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]

        sortierung = st.selectbox(
            "🔽 Ergebnisse sortieren nach:",
            ["Match-Rating (Höchste zuerst)", "Match-Rating (Niedrigste zuerst)", "Unternehmensname (A-Z)"]
        )
        
        if sortierung == "Match-Rating (Höchste zuerst)":
            df_filtered = df_filtered.sort_values(by="Match-Rating", ascending=False)
        elif sortierung == "Match-Rating (Niedrigste zuerst)":
            df_filtered = df_filtered.sort_values(by="Match-Rating", ascending=True)
        elif sortierung == "Unternehmensname (A-Z)":
            df_filtered = df_filtered.sort_values(by="Unternehmensname", ascending=True)

        st.metric("Gefundene Unternehmen", len(df_filtered))
        
        st.markdown("### 📊 Analyse der Treffer")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Verteilung der Sterne-Ratings**")
            rating_counts = df_filtered["Match-Rating"].value_counts().sort_index()
            st.bar_chart(rating_counts)
            
        with col2:
            st.write("**Verteilung nach Branchen**")
            kat_counts = df_filtered["Kategorie"].value_counts()
            st.bar_chart(kat_counts)
        
        st.dataframe(
            df_filtered.drop(columns=["Begründung", "Adresse"]),
            width='stretch',
            hide_index=True,
            column_config={
                "Match-Rating": st.column_config.NumberColumn("Rating", format="%d ⭐"),
                "Website": st.column_config.LinkColumn("Website")
            }
        )
        
        st.markdown("---")
        st.subheader("📝 Detailansicht & KI-Bewertungen")
        for index, row in df_filtered.iterrows():
            with st.expander(f"🏢 {row['Unternehmensname']} | Rating: {row['Match-Rating']} ⭐ | Chancen: {row['Einstiegschancen']}"):
                st.write(f"**Was sie machen:** {row['Was sie machen']}")
                st.write(f"**KI-Begründung:** {row['Begründung']}")
                st.markdown(f"🔗 [Zur Unternehmenswebsite]({row['Website']})")

   # ---------------------------------------------------------
    # TAB 2: LIVE-ANALYSE FÜR DRITTE (SaaS)
    # ---------------------------------------------------------
    with tab2:
        st.subheader("🚀 Individuelle Live-Suche & Analyse")
        st.write("Suche live nach neuen Unternehmen in Osnabrück und prüfe die Passung.")
        
        if not api_bereit:
            st.error("⚠️ Gemini API-Schlüssel fehlt.")
            
        # Neues Eingabefeld für die Google Places Suche
        such_branche = st.text_input("Welche Branche suchst du in Osnabrück? (z.B. Kanzlei, Marketing, Logistik)", placeholder="Kanzlei")
        nutzer_profil = st.text_area("Lebenslauf oder Kurzprofil hier einfügen:", height=200, placeholder="Ich studiere Jura im 5. Semester...")
        
        if st.button("Google-Suche & KI-Analyse starten (Top 5)"):
            if not nutzer_profil or not such_branche:
                st.warning("Bitte gib eine Branche und ein Profil ein.")
            elif api_bereit:
                # 1. GOOGLE PLACES ABFRAGE
                st.info(f"Suche nach '{such_branche}' in Osnabrück auf Google Maps...")
                places_key = st.secrets["PLACES_API_KEY"]
                url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={such_branche}+in+Osnabrück&key={places_key}"
                
                try:
                    response = requests.get(url).json()
                    results = response.get('results', [])[:5] # Wir nehmen die Top 5 für den Test
                except Exception as e:
                    st.error(f"Fehler bei der Google-Suche: {e}")
                    results = []

                if results:
                    st.success(f"{len(results)} Unternehmen gefunden. Starte KI-Bewertung...")
                    
                    # 2. GEMINI BEWERTUNG
                    model = genai.GenerativeModel('gemini-pro')
                    progress_bar = st.progress(0)
                    
                    ergebnis_liste = []
                    
                    for i, place in enumerate(results):
                        firma = place.get('name', 'Unbekannt')
                        adresse = place.get('formatted_address', 'Keine Adresse')
                        
                        prompt = f"""
                        Du bist ein Karriere-Scout. 
                        Profil des Nutzers: '{nutzer_profil}'
                        Gefundenes Unternehmen: '{firma}'
                        
                        Bewerte kurz und prägnant in 2-3 Sätzen, ob und wie dieses Profil bei diesem Unternehmen (anhand des Namens/der Branche) nützlich sein könnte.
                        Gib am Ende ein Rating von 1/5 bis 5/5 Sternen.
                        """
                        
                        try:
                            ki_antwort = model.generate_content(prompt).text
                        except Exception as e:
                            ki_antwort = f"Fehler bei Bewertung: {e}"
                            
                        ergebnis_liste.append({
                            "Unternehmen": firma,
                            "Adresse": adresse,
                            "KI-Analyse": ki_antwort
                        })
                        
                        progress_bar.progress((i + 1) / len(results))
                        time.sleep(1) # API-Schutz
                    
                    # 3. ERGEBNISSE ANZEIGEN
                    st.markdown("### 🏆 Deine persönlichen Matches")
                    df_live = pd.DataFrame(ergebnis_liste)
                    st.dataframe(df_live, width='stretch', hide_index=True)
                else:
                    st.warning("Keine Unternehmen gefunden. Versuche einen anderen Suchbegriff.")
