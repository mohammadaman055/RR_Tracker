from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

DATABASE_URL = 'postgresql://tracker_w1tk_user:tXYf9dFiZlbmRlOTTAIOgvsXOiDn6Ouc@dpg-cu5uujl6l47c73bt8d00-a.oregon-postgres.render.com/tracker_w1tk'

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Check Database Connection
def check_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        logging.info("Database connection successful!")
        return True
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return False

# Database initialization
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Create water_turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS water_turns (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS water_current (
                id SERIAL PRIMARY KEY,
                currentIndex INTEGER NOT NULL
            )
        """)
        cursor.execute("""
            INSERT INTO water_current (id, currentIndex) VALUES (1, 0) ON CONFLICT (id) DO UPDATE SET currentIndex = EXCLUDED.currentIndex; """)

        # Create dustbin_turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dustbin_turns (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dustbin_current (
                id SERIAL PRIMARY KEY,
                currentIndex INTEGER NOT NULL
            )
        """)
        cursor.execute("""
            INSERT INTO dustbin_current (id, currentIndex)
            VALUES (1, 0)
            ON CONFLICT (id) DO UPDATE SET currentIndex = EXCLUDED.currentIndex
        """)

        conn.commit()
        conn.close()
        logging.info("Database initialized successfully!")
        return True
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        return False

# Hardcoded members and their PINs
water_members_with_pins = {
    "Saiteja": "1234",
    "Ratnesh": "2345",
    "Rohit": "3456",
    "Harithik": "4567",
    "Aman": "5678"
}

dustbin_members_with_pins = {
    "Aman": "1234",
    "Ratnesh": "2345",
    "Saiteja": "3456",
    "Debjith": "4567",
    "Harithik": "5678"
}

# Helper function to fetch state from the respective tracker
def get_tracker_state(tracker_name):
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        if tracker_name == "water":
            cursor.execute("SELECT currentIndex FROM water_current WHERE id = 1")
            result = cursor.fetchone()
            if result is None or "currentindex" not in result:
                raise ValueError("No valid data found in water_current table. Initialize the database properly.")
            currentIndex = result["currentindex"]

            cursor.execute("SELECT * FROM water_turns ORDER BY id DESC")
            history = [{"name": row["name"], "timestamp": row["timestamp"]} for row in cursor.fetchall()]
        elif tracker_name == "dustbin":
            cursor.execute("SELECT currentIndex FROM dustbin_current WHERE id = 1")
            result = cursor.fetchone()
            if result is None or "currentindex" not in result:
                raise ValueError("No valid data found in dustbin_current table. Initialize the database properly.")
            currentIndex = result["currentindex"]

            cursor.execute("SELECT * FROM dustbin_turns ORDER BY id DESC")
            history = [{"name": row["name"], "timestamp": row["timestamp"]} for row in cursor.fetchall()]
        return currentIndex, history
    except Exception as e:
        logging.error(f"Error fetching tracker state: {e}")
        raise
    finally:
        conn.close()

def mark_tracker_done(tracker_name, currentIndex, pin):
    members = water_members_with_pins if tracker_name == "water" else dustbin_members_with_pins
    current_member = list(members.keys())[currentIndex]

    if members[current_member] != pin:
        return {"success": False, "error": "Invalid PIN"}, 403

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if tracker_name == "water":
            cursor.execute("INSERT INTO water_turns (name, timestamp) VALUES (%s, %s)", (current_member, timestamp))
            nextIndex = (currentIndex + 1) % len(members)
            cursor.execute("UPDATE water_current SET currentIndex = %s WHERE id = 1", (nextIndex,))
        elif tracker_name == "dustbin":
            cursor.execute("INSERT INTO dustbin_turns (name, timestamp) VALUES (%s, %s)", (current_member, timestamp))
            nextIndex = (currentIndex + 1) % len(members)
            cursor.execute("UPDATE dustbin_current SET currentIndex = %s WHERE id = 1", (nextIndex,))

        conn.commit()
    finally:
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
    if not DATABASE_URL:
        logging.error("DATABASE_URL not set. Please configure the environment variable.")
        exit(1)

    if  init_db() and check_db_connection():
        port = int(os.environ.get("PORT", 5000))  # Default to port 5000 if PORT is not set
        app.run(host="0.0.0.0", port=port)
    else:
        logging.error("Server failed to start due to database issues.")
