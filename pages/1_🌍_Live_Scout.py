import streamlit as st
import requests
import pandas as pd # NEU: Für die Kartendaten
from supabase import create_client

st.set_page_config(page_title="Live Scout", page_icon="🌍")
st.title("🌍 Live Company Scout")
st.markdown("Suche zielgerichtet nach Unternehmen und übergebe sie direkt an deine Pipeline oder die KI-Analyse.")

# --- DATENBANK-VERBINDUNG ---
@st.cache_resource
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        return None

supabase = get_db()
places_api_key = st.secrets.get("PLACES_API_KEY", None)

if not places_api_key:
    st.error("⚠️ PLACES_API_KEY fehlt in den Streamlit Secrets.")
    st.stop()

# --- SESSION STATE FÜR SUCHERGEBNISSE ---
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "last_search_query" not in st.session_state:
    st.session_state.last_search_query = ""

# --- SUCHE & FILTER ---
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    such_branche = st.text_input("Branche / Rolle:", placeholder="z.B. IT Consulting")
with col2:
    such_ort = st.text_input("Stadt / Region:", placeholder="z.B. Dublin")
with col3:
    max_ergebnisse = st.slider("Anzahl:", 5, 20, 10, step=5)

# 1. API Aufruf ausführen
if st.button("🚀 Unternehmen suchen"):
    if such_branche and such_ort:
        with st.spinner("Suche über Google API (FinOps optimiert)..."):
            url = "https://places.googleapis.com/v1/places:searchText"
            
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": places_api_key,
                # NEU: places.location wurde zur Maske hinzugefügt für die Map!
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.id,places.location"
            }
            payload = {"textQuery": f"{such_branche} in {such_ort}"}
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                res = response.json()
                
                if response.status_code == 200:
                    places = res.get("places", [])
                    if places:
                        st.session_state.search_results = places[:max_ergebnisse]
                        st.session_state.last_search_query = f"{such_branche} in {such_ort}"
                    else:
                        st.warning("Keine passenden Unternehmen in dieser Region gefunden.")
                        st.session_state.search_results = []
                else:
                    st.error(f"Google API Fehler: {response.status_code}")
            except Exception as e:
                st.error(f"Systemfehler bei der Anfrage: {e}")
    else:
        st.warning("Bitte gib sowohl eine Branche als auch einen Ort ein.")

# 2. Suchergebnisse anzeigen (inklusive interaktiver Karte!)
if st.session_state.search_results:
    st.success(f"✅ {len(st.session_state.search_results)} Unternehmen für '{st.session_state.last_search_query}' gefunden!")
    
    # --- NEU: DIE INTERAKTIVE KARTE ---
    # Wir filtern die GPS-Daten aus den Google-Ergebnissen
    map_data = []
    for place in st.session_state.search_results:
        loc = place.get("location")
        if loc:
            map_data.append({"lat": loc.get("latitude"), "lon": loc.get("longitude")})
            
    if map_data:
        st.subheader("🗺️ Standort-Übersicht")
        df_map = pd.DataFrame(map_data)
        # Streamlit plottet diese Daten automatisch auf einer interaktiven Map
        st.map(df_map, zoom=12, use_container_width=True)
        st.divider()

    # --- DIE LISTENANSICHT ---
    for place in st.session_state.search_results:
        name = place.get("displayName", {}).get("text", "Unbekannt")
        adresse = place.get("formattedAddress", "Keine Adresse hinterlegt")
        place_id = place.get("id")
        
        with st.container(border=True):
            st.subheader(f"🏢 {name}")
            st.write(f"📍 {adresse}")
            
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if st.button(f"➕ Zur Pipeline hinzufügen", key=f"pipe_{place_id}"):
                    if supabase:
                        new_entry = {"unternehmen": name, "rolle": "Initiativ", "status": "Neu", "notizen": adresse}
                        supabase.table("pipeline").insert(new_entry).execute()
                        st.toast(f"✅ {name} im Dashboard gespeichert!", icon="💾")
                    else:
                        st.error("Datenbankverbindung fehlt.")
            
            with btn_col2:
                if st.button(f"🤖 KI-Match prüfen", key=f"ki_{place_id}", type="primary"):
                    st.session_state.analyze_company_name = name
                    st.session_state.analyze_company_details = f"Adresse: {adresse}\nBranche gesucht: {st.session_state.last_search_query}"
                    st.switch_page("pages/3_🧠_KI_Analyse.py")
