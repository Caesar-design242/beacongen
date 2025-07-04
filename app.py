# 📁 app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
import sqlite3
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

def init_db():
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS surveyors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        prefix TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL,
        company TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS beacon_counter (
        id INTEGER PRIMARY KEY,
        current_alpha TEXT NOT NULL DEFAULT 'AA',
        current_number INTEGER NOT NULL DEFAULT 0
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS beacon_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        surveyor_prefix TEXT NOT NULL,
        surveyor_name TEXT NOT NULL,
        beacon_codes TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        quarter TEXT NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS quarterly_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        surveyor_prefix TEXT NOT NULL,
        quarter TEXT NOT NULL,
        usage_count INTEGER NOT NULL DEFAULT 0,
        UNIQUE(surveyor_prefix, quarter)
    )''')
    cursor.execute('SELECT COUNT(*) FROM beacon_counter')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO beacon_counter (id, current_alpha, current_number) VALUES (1, "AA", 0)')
    conn.commit()
    conn.close()

@app.before_first_request
def setup():
    init_db()

def get_current_quarter():
    now = datetime.now()
    quarter = (now.month - 1) // 3 + 1
    return f"{now.year}-Q{quarter}"

def get_next_beacon_codes(quantity):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT current_alpha, current_number FROM beacon_counter WHERE id = 1')
    alpha, number = cursor.fetchone()
    codes = []
    for _ in range(quantity):
        number += 1
        if number > 9999:
            number = 1
            if alpha[1] == 'Z':
                alpha = chr(ord(alpha[0])+1) + 'A'
            else:
                alpha = alpha[0] + chr(ord(alpha[1])+1)
        codes.append(f"SC/ED {alpha} {number:04d}")
    cursor.execute('UPDATE beacon_counter SET current_alpha = ?, current_number = ? WHERE id = 1', (alpha, number))
    conn.commit()
    conn.close()
    return codes

def get_surveyor(identifier):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM surveyors WHERE prefix = ? COLLATE NOCASE', (identifier,))
    row = cursor.fetchone()
    if not row:
        cursor.execute('SELECT * FROM surveyors WHERE name LIKE ? COLLATE NOCASE', (f"%{identifier}%",))
        row = cursor.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'prefix': row[2], 'status': row[3], 'company': row[4], 'address': row[5], 'phone': row[6], 'email': row[7]}
    return None

def get_quarterly_usage(prefix, quarter):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT usage_count FROM quarterly_usage WHERE surveyor_prefix = ? AND quarter = ?', (prefix, quarter))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_quarterly_usage(prefix, quarter, quantity):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO quarterly_usage (surveyor_prefix, quarter, usage_count)
                      VALUES (?, ?, COALESCE((SELECT usage_count FROM quarterly_usage WHERE surveyor_prefix = ? AND quarter = ?), 0) + ?)''',
                      (prefix, quarter, prefix, quarter, quantity))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier'].strip().upper()
        if not identifier:
            flash('Please enter name or prefix', 'danger')
            return render_template('login.html')
        surveyor = get_surveyor(identifier)
        if surveyor:
            session['surveyor'] = surveyor
            return redirect(url_for('dashboard'))
        else:
            flash('Surveyor not found.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    surveyor = session['surveyor']
    quarter = get_current_quarter()
    usage = get_quarterly_usage(surveyor['prefix'], quarter)
    remaining = max(0, 200 - usage)
    return render_template('dashboard.html', surveyor=surveyor, quarter=quarter, usage=usage, remaining=remaining)

@app.route('/generate', methods=['POST'])
def generate_beacons():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    surveyor = session['surveyor']
    quantity = int(request.form.get('quantity', 0))
    quarter = get_current_quarter()
    usage = get_quarterly_usage(surveyor['prefix'], quarter)
    if quantity <= 0 or quantity + usage > 200:
        flash('Invalid quantity or exceeds quarterly limit', 'danger')
        return redirect(url_for('dashboard'))
    codes = get_next_beacon_codes(quantity)
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO beacon_logs (surveyor_prefix, surveyor_name, beacon_codes, quantity, quarter)
                      VALUES (?, ?, ?, ?, ?)''',
                   (surveyor['prefix'], surveyor['name'], '\n'.join(codes), quantity, quarter))
    conn.commit()
    conn.close()
    update_quarterly_usage(surveyor['prefix'], quarter, quantity)
    return render_template('result.html', surveyor=surveyor, beacon_codes=codes, quantity=quantity)

@app.route('/history')
def history():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT beacon_codes, quantity, generated_at, quarter FROM beacon_logs WHERE surveyor_prefix = ? ORDER BY generated_at DESC''', (session['surveyor']['prefix'],))
    logs = cursor.fetchall()
    conn.close()
    return render_template('history.html', logs=logs, surveyor=session['surveyor'])

@app.route('/export_csv')
def export_csv():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT beacon_codes, generated_at, quarter FROM beacon_logs WHERE surveyor_prefix = ? ORDER BY generated_at DESC''', (session['surveyor']['prefix'],))
    logs = cursor.fetchall()
    conn.close()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Beacon Code', 'Generated At', 'Quarter'])
    for codes, gen_time, quarter in logs:
        for code in codes.split('\n'):
            writer.writerow([code, gen_time, quarter])
    return Response(output.getvalue(), mimetype='text/csv', headers={"Content-disposition": f"attachment; filename=beacon_codes_{session['surveyor']['prefix']}.csv"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=10000)
