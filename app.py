import sqlite3
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

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

# --- Helper Functions ---
def get_inventory_text():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT room_type, price_per_night, available_rooms FROM rooms")
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([f"- {r[0]}: Rs. {r[1]}/night ({r[2]} available)" for r in rows])

# --- AI Engine (Groq Llama-3.3) ---
API_KEY = "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"
llm = ChatGroq(model_name="llama-3.1-8b-instant", groq_api_key=API_KEY, temperature=0.3)

# --- UI Setup ---
st.set_page_config(page_title="Grand Stay 24/7 AI", page_icon="🏨", layout="wide")
tab1, tab2 = st.tabs(["💬 Guest Assistant", "📊 Lead Dashboard (Admin)"])

with tab1:
    st.title("🏨 Grand Stay 24/7 AI Concierge")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.write(msg.content)

    if query := st.chat_input("Puchiye: room rates, facilities ya booking..."):
        with st.chat_message("user"):
            st.write(query)

        current_inventory = get_inventory_text()
        system_instruction = f"""Aap ek polite aur smart Hotel Receptionist AI Concierge hain.
Hamesha polite Hinglish ya English me baat karein.
Hotel details:
- Check-in: 12:00 PM | Check-out: 11:00 AM
- Free Wi-Fi aur breakfast included hai. Swimming pool 7 AM to 8 PM open rehta hai.
Current Live Inventory & Rates:
{current_inventory}

Guest ka sawal handle karein. Agar guest booking chahe ya price discuss kare, toh unka Name aur Phone Number maangein taaki booking confirm ho sake."""

        messages = [SystemMessage(content=system_instruction)] + st.session_state.chat_history + [HumanMessage(content=query)]
        
        with st.chat_message("assistant"):
            with st.spinner("AI reply taiyar ho raha hai..."):
                response = llm.invoke(messages)
                st.write(response.content)

        st.session_state.chat_history.append(HumanMessage(content=query))
        st.session_state.chat_history.append(AIMessage(content=response.content))

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
