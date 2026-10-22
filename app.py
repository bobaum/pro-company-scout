import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Company Scout Osnabrück", layout="wide")
st.title("🎯 Company Scout Osnabrück")
st.markdown("Deine bereinigte Übersicht für PMO, IT-Projektkoordination und Consulting.")

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
    
    st.sidebar.header("⚙️ Filter-Optionen")
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

    # --- Sortier-Logik ---
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
    
    # --- Datenvisualisierung ---
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
    
    # --- Kompakte Übersichtstabelle ---
    st.dataframe(
        df_filtered.drop(columns=["Begründung", "Adresse"]),
        width='stretch',
        hide_index=True,
        column_config={
            "Match-Rating": st.column_config.NumberColumn("Rating", format="%d ⭐"),
            "Website": st.column_config.LinkColumn("Website")
        }
    )
    
    # --- Interaktive Detailansicht mit Expandern ---
    st.markdown("---")
    st.subheader("📝 Detailansicht & KI-Bewertungen")
    
    for index, row in df_filtered.iterrows():
        with st.expander(f"🏢 {row['Unternehmensname']} | Rating: {row['Match-Rating']} ⭐ | Chancen: {row['Einstiegschancen']}"):
            st.write(f"**Was sie machen:** {row['Was sie machen']}")
            st.write(f"**KI-Begründung:** {row['Begründung']}")
            st.markdown(f"🔗 [Zur Unternehmenswebsite]({row['Website']})")

except Exception as e:
    st.error(f"Fehler beim Laden: {e}")