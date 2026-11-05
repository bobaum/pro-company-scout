import streamlit as st
import requests
from supabase import create_client, Client

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

# --- SUCHE & FILTER ---
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    such_branche = st.text_input("Branche / Rolle:", placeholder="z.B. IT Consulting, PMO")
with col2:
    such_ort = st.text_input("Stadt / Region:", placeholder="z.B. Dublin, Osnabrück")
with col3:
    # NEU: Slider für die Anzahl der Ergebnisse
    max_ergebnisse = st.slider("Anzahl:", 5, 20, 10, step=5)

if st.button("🚀 Unternehmen suchen"):
    if such_branche and such_ort:
        with st.spinner("Suche über Google API (FinOps optimiert)..."):
            url = "https://places.googleapis.com/v1/places:searchText"
            
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": places_api_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.id"
            }
            payload = {"textQuery": f"{such_branche} in {such_ort}"}
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                res = response.json()
                
                if response.status_code == 200:
                    places = res.get("places", [])
                    if places:
                        # Wir beschränken das Ergebnis auf die vom User gewählte Anzahl
                        treffer = places[:max_ergebnisse]
                        st.success(f"✅ {len(treffer)} Unternehmen gefunden!")
                        
                        for place in treffer:
                            name = place.get("displayName", {}).get("text", "Unbekannt")
                            adresse = place.get("formattedAddress", "Keine Adresse hinterlegt")
                            place_id = place.get("id")
                            
                            with st.container(border=TeamBorder if 'TeamBorder' in globals() else True):
                                st.subheader(f"🏢 {name}")
                                st.write(f"📍 {adresse}")
                                
                                btn_col1, btn_col2 = st.columns(2)
                                
                                with btn_col1:
                                    if st.button(f"➕ Zur Pipeline hinzufügen", key=f"pipe_{place_id}"):
                                        if supabase:
                                            new_entry = {"unternehmen": name, "rolle": f"Initiativ ({such_branche})", "status": "Neu", "notizen": adresse}
                                            supabase.table("pipeline").insert(new_entry).execute()
                                            st.success(f"{name} im Dashboard gespeichert!")
                                        else:
                                            st.error("Datenbankverbindung fehlt.")
                                
                                with btn_col2:
                                    if st.button(f"🤖 KI-Match prüfen", key=f"ki_{place_id}", type="primary"):
                                        st.session_state.analyze_company_name = name
                                        st.session_state.analyze_company_details = f"Adresse: {adresse}\nBranche: {such_branche}"
                                        
                                        # NEU: Ein direkter visueller Hinweis, dass es geklappt hat
                                        st.toast(f"✅ {name} für Analyse übernommen! Klicke links auf 'KI-Analyse'.", icon="🚀")
                    else:
                        st.warning("Keine passenden Unternehmen in dieser Region gefunden.")
                else:
                    st.error(f"Google API Fehler: {response.status_code}")
            except Exception as e:
                st.error(f"Systemfehler bei der Anfrage: {e}")
    else:
        st.warning("Bitte gib sowohl eine Branche als auch einen Ort ein.")
