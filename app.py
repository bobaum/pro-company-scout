import streamlit as st
import pandas as pd
import re
import google.generativeai as genai
import time
from supabase import create_client, Client
import requests

st.set_page_config(page_title="Company Scout Osnabrück", layout="wide")
st.title("🎯 Company Scout Osnabrück")

# --- API Key aus den Streamlit Secrets laden ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    api_bereit = True
except Exception:
    api_bereit = False

# --- Supabase Datenbank laden ---
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
    db_bereit = True
except Exception:
    db_bereit = False

@st.cache_data
def load_and_clean_data():
    try:
        df = pd.read_excel("osnabrueck_matched.xlsx")
    except Exception as e:
        st.error(f"Excel-Datei konnte nicht geladen werden: {e}")
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

    def clean_kategorie(val):
        val = str(val).lower()
        if "consulting" in val or "beratung" in val: return "Consulting & Beratung"
        if "it" in val or "software" in val or "system" in val or "cloud" in val: return "IT & Tech"
        if "logistik" in val or "transport" in val or "spedition" in val: return "Logistik & SCM"
        if "industrie" in val or "produktion" in val or "fertigung" in val: return "Industrie"
        if "holding" in val or "finanz" in val: return "Finance & Holding"
        return "Wirtschaft & Sonstiges"

    if not df.empty:
        df["Match-Rating"] = df["Match-Rating"].apply(clean_rating)
        df["Einstiegschancen"] = df["Einstiegschancen"].apply(clean_chancen)
        df["Kategorie"] = df["Kategorie"].apply(clean_kategorie)
    return df

df = load_and_clean_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📊 Datenbank (PMO & IT)", "🤖 Neue Live-Analyse (SaaS)"])
    
    # ---------------------------------------------------------
    # TAB 1: DEINE BESTEHENDE DATENBANK
    # ---------------------------------------------------------
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
        
        cols_to_drop = [col for col in ["Begründung", "Adresse"] if col in df_filtered.columns]
        
        st.dataframe(
            df_filtered.drop(columns=cols_to_drop),
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
                was_sie_machen = row['Was sie machen'] if 'Was sie machen' in row else 'Keine Info'
                begruendung = row['Begründung'] if 'Begründung' in row else 'Keine Info'
                website = row['Website'] if 'Website' in row else '#'
                
                st.write(f"**Was sie machen:** {was_sie_machen}")
                st.write(f"**KI-Begründung:** {begruendung}")
                st.markdown(f"🔗 [Zur Unternehmenswebsite]({website})")

    # ---------------------------------------------------------
# TAB 2: BEWERBUNGS-PIPELINE (Supabase PostgreSQL)
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
            
            # Falls die Tabelle noch komplett leer ist, initialisiere die Spalten
            if df_pipeline.empty:
                df_pipeline = pd.DataFrame(columns=["unternehmen", "rolle", "status", "deadline", "notizen"])
            
            # 2. Interaktive Tabelle anzeigen
            edited_df = st.data_editor(
                df_pipeline, 
                num_rows="dynamic",
                use_container_width="stretch",
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Neu", "In Vorbereitung", "Beworben", "Interview", "Angebot", "Abgesagt"]
                    )
                }
            )
            
            # 3. Speichern-Button
            if st.button("💾 Änderungen in Cloud speichern"):
                # Entferne leere Zeilen, bei denen kein Unternehmen eingetragen wurde
                valid_data = edited_df[edited_df["unternehmen"].astype(str).str.strip() != ""]
                records = valid_data.to_dict(orient="records")
                
                if records:
                    # Upsert überschreibt bestehende Einträge (anhand des Unternehmens-Namens) oder legt neue an
                    supabase.table("pipeline").upsert(records).execute()
                    st.success("✅ Pipeline erfolgreich synchronisiert!")
                else:
                    st.warning("Keine gültigen Daten zum Speichern gefunden.")
                    
        except Exception as e:
            st.error(f"Fehler bei der Datenbank-Aktion: {e}")
