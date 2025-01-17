from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect("trackers.db")
    cursor = conn.cursor()

    # Create water_turns table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_current (
            id INTEGER PRIMARY KEY,
            currentIndex INTEGER NOT NULL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO water_current (id, currentIndex) VALUES (1, 0)")

    # Create dustbin_turns table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dustbin_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dustbin_current (
            id INTEGER PRIMARY KEY,
            currentIndex INTEGER NOT NULL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO dustbin_current (id, currentIndex) VALUES (1, 0)")

    conn.commit()
    conn.close()

init_db()

# Hardcoded members and their PINs
water_members_with_pins = {
    "Person 1": "1234",
    "Person 2": "2345",
    "Person 3": "3456",
    "Person 4": "4567",
    "Person 5": "5678"
}

dustbin_members_with_pins = {
    "Person 1": "1234",
    "Person 2": "2345",
    "Person 3": "3456",
    "Person 4": "4567",
    "Person 5": "5678"
}

# Helper function to fetch state from the respective tracker
def get_tracker_state(tracker_name):
    conn = sqlite3.connect("trackers.db")
    cursor = conn.cursor()
    
    if tracker_name == "water":
        cursor.execute("SELECT currentIndex FROM water_current WHERE id = 1")
        currentIndex = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM water_turns ORDER BY id DESC")
        history = [{"name": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
    elif tracker_name == "dustbin":
        cursor.execute("SELECT currentIndex FROM dustbin_current WHERE id = 1")
        currentIndex = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM dustbin_turns ORDER BY id DESC")
        history = [{"name": row[1], "timestamp": row[2]} for row in cursor.fetchall()]

    conn.close()
    return currentIndex, history

# Helper function to mark a turn as done in the respective tracker
def mark_tracker_done(tracker_name, currentIndex, pin):
    members = water_members_with_pins if tracker_name == "water" else dustbin_members_with_pins

    current_member = list(members.keys())[currentIndex]

    # Check if the PIN is correct
    if members[current_member] != pin:
        return {"success": False, "error": "Invalid PIN"}, 403

    conn = sqlite3.connect("trackers.db")
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if tracker_name == "water":
        cursor.execute("INSERT INTO water_turns (name, timestamp) VALUES (?, ?)", (current_member, timestamp))
        nextIndex = (currentIndex + 1) % len(members)
        cursor.execute("UPDATE water_current SET currentIndex = ? WHERE id = 1", (nextIndex,))
    elif tracker_name == "dustbin":
        cursor.execute("INSERT INTO dustbin_turns (name, timestamp) VALUES (?, ?)", (current_member, timestamp))
        nextIndex = (currentIndex + 1) % len(members)
        cursor.execute("UPDATE dustbin_current SET currentIndex = ? WHERE id = 1", (nextIndex,))

    conn.commit()
    conn.close()

    return {"success": True}, 200

# Water Tracker API
@app.route("/water/state", methods=["GET"])
def water_state():
    currentIndex, history = get_tracker_state("water")
    return jsonify({"currentIndex": currentIndex, "history": history})

@app.route("/water/mark-done", methods=["POST"])
def water_mark_done():
    data = request.json
    currentIndex = data["currentIndex"]
    pin = data["pin"]
    return jsonify(mark_tracker_done("water", currentIndex, pin))

# Dustbin Tracker API
@app.route("/dustbin/state", methods=["GET"])
def dustbin_state():
    currentIndex, history = get_tracker_state("dustbin")
    return jsonify({"currentIndex": currentIndex, "history": history})

@app.route("/dustbin/mark-done", methods=["POST"])
def dustbin_mark_done():
    data = request.json
    currentIndex = data["currentIndex"]
    pin = data["pin"]
    return jsonify(mark_tracker_done("dustbin", currentIndex, pin))

if __name__ == "__main__":
    app.run(debug=True)
