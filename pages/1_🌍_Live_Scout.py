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

# --- SUCHE ---
col1, col2 = st.columns(2)
with col1:
    such_branche = st.text_input("Branche / Rolle:", placeholder="z.B. IT Consulting, PMO")
with col2:
    such_ort = st.text_input("Stadt / Region:", placeholder="z.B. Dublin, Osnabrück")

if st.button("🚀 Unternehmen suchen"):
    if such_branche and such_ort:
        with st.spinner("Suche über Google API (FinOps optimiert)..."):
            url = "https://places.googleapis.com/v1/places:searchText"
            
            # FINOPS: Wir fragen NUR Name, Adresse und ID ab, um unnötige API-Kosten zu vermeiden.
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
                        treffer = places[:15]
                        st.success(f"✅ {len(treffer)} Unternehmen gefunden!")
                        
                        for place in treffer:
                            name = place.get("displayName", {}).get("text", "Unbekannt")
                            adresse = place.get("formattedAddress", "Keine Adresse hinterlegt")
                            place_id = place.get("id")
                            
                            # Visuelle Container für jedes Unternehmen (macht das UI sauberer als einfache Textzeilen)
                            with st.container(border=True):
                                st.subheader(f"🏢 {name}")
                                st.write(f"📍 {adresse}")
                                
                                # Zwei Buttons nebeneinander
                                btn_col1, btn_col2 = st.columns(2)
                                
                                with btn_col1:
                                    if st.button(f"➕ Zur Pipeline hinzufügen", key=f"pipe_{place_id}"):
                                        if supabase:
                                            new_entry = {"unternehmen": name, "rolle": f"Initiativ ({such_branche})", "status": "Neu", "notizen": adresse}
                                            supabase.table("pipeline").insert(new_entry).execute()
                                            st.success(f"{name} wurde im Dashboard gespeichert!")
                                        else:
                                            st.error("Datenbankverbindung fehlt.")
                                
                                with btn_col2:
                                    # Der blaue Primary-Button für die KI
                                    if st.button(f"🤖 KI-Match prüfen", key=f"ki_{place_id}", type="primary"):
                                        # Hier befüllen wir das Gedächtnis der App (Session State)!
                                        st.session_state.analyze_company_name = name
                                        st.session_state.analyze_company_details = f"Adresse: {adresse}\nBranche: {such_branche}"
                                        st.success(f"✅ {name} ist für die Analyse bereit! Wechsle nun in der Navigation zum KI-Match.")
                                        
                    else:
                        st.warning("Keine passenden Unternehmen in dieser Region gefunden.")
                else:
                    st.error(f"Google API Fehler: {response.status_code}")
                    st.write(res.get("error", {}).get("message", ""))
            except Exception as e:
                st.error(f"Systemfehler bei der Anfrage: {e}")
    else:
        st.warning("Bitte gib sowohl eine Branche als auch einen Ort ein.")
