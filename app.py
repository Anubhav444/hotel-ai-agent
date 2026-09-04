import sqlite3
import streamlit as st
from langchain.tools import tool
from langchain_groq import ChatGroq
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

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

# --- Tools ---
@tool
def check_room_availability() -> str:
    """Current available rooms aur pricing check karta hai."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT room_type, price_per_night, available_rooms FROM rooms")
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([f"- {r[0]}: Rs. {r[1]}/night ({r[2]} available)" for r in rows])

@tool
def capture_lead_and_book(guest_name: str, phone: str, room_type: str, nights: int) -> str:
    """Lead capture karta hai aur room booking confirm karta hai."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO leads (guest_name, guest_phone, interest) VALUES (?, ?, ?)",
                   (guest_name, phone, f"{room_type} for {nights} nights"))
    
    cursor.execute("SELECT price_per_night, available_rooms FROM rooms WHERE LOWER(room_type) LIKE LOWER(?)", (f"%{room_type}%",))
    res = cursor.fetchone()
    
    if not res or res[1] <= 0:
        conn.commit()
        conn.close()
        return f"Maafi chahte hain, {room_type} filhaal full hai. Hamari team aapse {phone} par contact karegi."
    
    total = res[0] * int(nights)
    cursor.execute("UPDATE rooms SET available_rooms = available_rooms - 1 WHERE LOWER(room_type) LIKE LOWER(?)", (f"%{room_type}%",))
    conn.commit()
    conn.close()
    
    return f"Booking Confirmed! Guest: {guest_name} | Room: {room_type} | Nights: {nights} | Total: Rs. {total}. Hamari front desk team aapse sampark karegi."

# --- AI Setup ---
API_KEY = "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"
llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=API_KEY, temperature=0.3)
tools = [check_room_availability, capture_lead_and_book]

prompt = ChatPromptTemplate.from_messages([
    ("system", """Aap ek smart Hotel Concierge AI hain. 
Aapka mission hai guests ki inquiries solve karna aur unhe booking ke liye guide karna.
Jab bhi koi guest booking chahe ya price discuss kare, unka Name aur Phone number zaroor maangein taaki 'capture_lead_and_book' execute ho sake.
Check-in time 12 PM hai aur Check-out 11 AM."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# --- Web UI ---
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
            
    if query := st.chat_input("Puchiye: room rates, policies ya booking..."):
        with st.chat_message("user"):
            st.write(query)
        with st.chat_message("assistant"):
            with st.spinner("AI reply taiyar ho raha hai..."):
                res = agent_executor.invoke({"input": query, "chat_history": st.session_state.chat_history})
                st.write(res["output"])
        st.session_state.chat_history.append(HumanMessage(content=query))
        st.session_state.chat_history.append(AIMessage(content=res["output"]))

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
