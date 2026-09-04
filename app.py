import sqlite3
import streamlit as st
from groq import Groq

# --- Database Setup ---
DB_FILE = "hotel_leads.db"
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS rooms (
    room_type TEXT PRIMARY KEY,
    price_per_night REAL,
    available_rooms INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_name TEXT,
    guest_phone TEXT,
    interest TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("INSERT OR IGNORE INTO rooms VALUES ('Deluxe Room', 3500, 4)")
cursor.execute("INSERT OR IGNORE INTO rooms VALUES ('Standard Room', 2000, 6)")
cursor.execute("INSERT OR IGNORE INTO rooms VALUES ('Suite', 6000, 2)")
conn.commit()
conn.close()

def get_inventory_text():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT room_type, price_per_night, available_rooms FROM rooms")
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([f"- {r[0]}: Rs. {r[1]}/night ({r[2]} available)" for r in rows])

# Client initialization via secrets
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="Grand Stay 24/7 AI", page_icon="🏨", layout="wide")
tab1, tab2 = st.tabs(["💬 Guest Assistant", "📊 Lead Dashboard (Admin)"])

with tab1:
    st.title("🏨 Grand Stay 24/7 AI Concierge")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if query := st.chat_input("Puchiye: room rates, facilities ya booking..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)

        current_inventory = get_inventory_text()
        system_prompt = f"""Aap ek polite aur helpful Hotel Concierge AI hain.
Hamesha natural Hindi/Hinglish me baat karein.
Hotel details:
- Check-in: 12 PM | Check-out: 11 AM
- Free Wi-Fi aur Breakfast shamil hai. Swimming pool 7 AM to 8 PM open rehta hai.
Current Available Rooms:
{current_inventory}

Guest ki inquiry resolve karein aur unka Name aur Phone number maangein taaki booking confirm ho sake."""

        conversation = [{"role": "system", "content": system_prompt}] + st.session_state.messages

        with st.chat_message("assistant"):
            with st.spinner("AI reply taiyar ho raha hai..."):
                try:
                    chat_completion = client.chat.completions.create(
                        messages=conversation,
                        model="gemma2-9b-it",
                    )
                    response_text = chat_completion.choices[0].message.content
                    st.write(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"API Error: {str(e)}")

with tab2:
    st.subheader("Captured Leads")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, guest_name, guest_phone, interest, timestamp FROM leads ORDER BY id DESC")
    leads_data = cursor.fetchall()
    conn.close()

    if leads_data:
        st.table([{
            "ID": l[0], 
            "Guest Name": l[1], 
            "Phone": l[2], 
            "Details": l[3], 
            "Date/Time": l[4]
        } for l in leads_data])
    else:
        st.info("Abhi koi lead capture nahi hui hai.")
