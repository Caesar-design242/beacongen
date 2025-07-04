from flask import Flask, render_template, request
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS surveyors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    prefix TEXT UNIQUE,
                    quarter_count INTEGER DEFAULT 0,
                    last_request TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS beacons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    surveyor_id INTEGER,
                    generated_on TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY,
                    last_serial INTEGER
                )''')
    c.execute("INSERT OR IGNORE INTO settings (id, last_serial) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

def generate_beacons(prefix, quantity):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Fetch surveyor
    c.execute("SELECT id, quarter_count FROM surveyors WHERE prefix = ?", (prefix,))
    row = c.fetchone()
    if not row:
        return f"Surveyor {prefix} not found", []
    
    surveyor_id, count = row
    if count + quantity > 200:
        return "Quota exceeded", []

    # Get last serial
    c.execute("SELECT last_serial FROM settings WHERE id = 1")
    last_serial = c.fetchone()[0]

    codes = []
    for i in range(quantity):
        serial_num = last_serial + i + 1
        alpha_prefix = chr(65 + (serial_num // 10000)) + chr(65 + ((serial_num // 1000) % 10))
        number_part = f"{serial_num % 10000:04}"
        code = f"SC/ED {alpha_prefix} {number_part} {prefix}"
        codes.append(code)
        c.execute("INSERT INTO beacons (code, surveyor_id, generated_on) VALUES (?, ?, ?)",
                  (code, surveyor_id, datetime.now().isoformat()))
    
    # Update counters
    c.execute("UPDATE surveyors SET quarter_count = quarter_count + ?, last_request = ? WHERE id = ?",
              (quantity, datetime.now().isoformat(), surveyor_id))
    c.execute("UPDATE settings SET last_serial = ?", (last_serial + quantity,))
    
    conn.commit()
    conn.close()
    return "Success", codes

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    codes = []
    if request.method == 'POST':
        prefix = request.form['prefix']
        qty = int(request.form['quantity'])
        message, codes = generate_beacons(prefix, qty)
    return render_template('index.html', message=message, codes=codes)

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=False, host='0.0.0.0', port=port)
