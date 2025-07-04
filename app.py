from flask import Flask, render_template, request
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# ================================
# Database Initialization
# ================================
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Surveyor table
    c.execute('''CREATE TABLE IF NOT EXISTS surveyors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    prefix TEXT UNIQUE,
                    quarter_count INTEGER DEFAULT 0,
                    last_request TEXT
                )''')

    # Beacon table
    c.execute('''CREATE TABLE IF NOT EXISTS beacons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    surveyor_id INTEGER,
                    generated_on TEXT
                )''')

    # Serial tracker
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY,
                    last_serial INTEGER
                )''')

    # Initialize counter
    c.execute("INSERT OR IGNORE INTO settings (id, last_serial) VALUES (1, 0)")
    conn.commit()
    conn.close()

init_db()

# ================================
# Add Surveyor to DB
# ================================
def add_surveyor(name, prefix):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO surveyors (name, prefix) VALUES (?, ?)", (name.upper(), prefix.upper()))
        conn.commit()
        print(f"Surveyor {name} ({prefix}) added.")
    except sqlite3.IntegrityError:
        print("Prefix already exists.")
    conn.close()

# ================================
# Beacon Generation Logic
# ================================
def generate_beacons(prefix, quantity):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Check surveyor
    c.execute("SELECT id, quarter_count FROM surveyors WHERE prefix = ?", (prefix,))
    row = c.fetchone()
    if not row:
        return f"Surveyor {prefix} not found", []

    surveyor_id, count = row
    if count + quantity > 200:
        return "Quota exceeded (max 200 per quarter).", []

    # Last serial
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

    # Update counter
    c.execute("UPDATE surveyors SET quarter_count = quarter_count + ?, last_request = ? WHERE id = ?",
              (quantity, datetime.now().isoformat(), surveyor_id))
    c.execute("UPDATE settings SET last_serial = ?", (last_serial + quantity,))
    conn.commit()
    conn.close()

    return "Success", codes

# ================================
# Homepage – Request Beacons
# ================================
@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    codes = []
    show_add_form = False
    missing_prefix = ''

    if request.method == 'POST':
        prefix = request.form.get('prefix', '').strip().upper()
        qty = int(request.form.get('quantity', 0))

        print("🔍 Checking surveyor with prefix:", prefix)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM surveyors WHERE prefix = ?", (prefix,))
        row = c.fetchone()
        conn.close()

        if not row:
            print("🟥 Surveyor not found.")
            show_add_form = True
            missing_prefix = prefix
        else:
            message, codes = generate_beacons(prefix, qty)

    return render_template('index.html', message=message, codes=codes,
                           show_add_form=show_add_form, missing_prefix=missing_prefix)

# ================================
# Route to Add Surveyor Manually
# ================================
@app.route('/add_surveyor', methods=['POST'])
def handle_add_surveyor():
    name = request.form['name']
    prefix = request.form['prefix'].strip().upper()
    add_surveyor(name, prefix)
    return render_template('index.html', message=f"✅ Surveyor {name} added. Now you can generate beacons.",
                           codes=[], show_add_form=False)

# ================================
# Launch App
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
