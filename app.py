from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
import sqlite3
import os
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change to a secure key

# --- Initialize the Database ---
def init_db():
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()

    # Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surveyors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            prefix TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            company TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beacon_counter (
            id INTEGER PRIMARY KEY,
            current_alpha TEXT NOT NULL DEFAULT 'AA',
            current_number INTEGER NOT NULL DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beacon_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surveyor_prefix TEXT NOT NULL,
            surveyor_name TEXT NOT NULL,
            beacon_codes TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            quarter TEXT NOT NULL,
            FOREIGN KEY (surveyor_prefix) REFERENCES surveyors (prefix)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quarterly_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surveyor_prefix TEXT NOT NULL,
            quarter TEXT NOT NULL,
            usage_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(surveyor_prefix, quarter),
            FOREIGN KEY (surveyor_prefix) REFERENCES surveyors (prefix)
        )
    ''')

    # Init counter
    cursor.execute('SELECT COUNT(*) FROM beacon_counter')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO beacon_counter (id, current_alpha, current_number) VALUES (1, "AA", 0)')

    conn.commit()
    conn.close()

# --- Helper Functions ---
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
    current_alpha = alpha
    current_number = number

    for _ in range(quantity):
        current_number += 1
        if current_number > 9999:
            current_number = 10
            if current_alpha[1] == 'Z':
                if current_alpha[0] == 'Z':
                    current_alpha = 'AA'
                else:
                    current_alpha = chr(ord(current_alpha[0]) + 1) + 'A'
            else:
                current_alpha = current_alpha[0] + chr(ord(current_alpha[1]) + 1)

        code = f"{current_alpha} {current_number:04d}"
        codes.append(code)

    cursor.execute('UPDATE beacon_counter SET current_alpha = ?, current_number = ? WHERE id = 1',
                   (current_alpha, current_number))
    conn.commit()
    conn.close()
    return codes

def get_quarterly_usage(surveyor_prefix, quarter):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT usage_count FROM quarterly_usage WHERE surveyor_prefix = ? AND quarter = ?''',
                   (surveyor_prefix, quarter))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_quarterly_usage(surveyor_prefix, quarter, amount):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO quarterly_usage (surveyor_prefix, quarter, usage_count)
        VALUES (?, ?, COALESCE((SELECT usage_count FROM quarterly_usage WHERE surveyor_prefix = ? AND quarter = ?), 0) + ?)
    ''', (surveyor_prefix, quarter, surveyor_prefix, quarter, amount))
    conn.commit()
    conn.close()

def get_surveyor_by_prefix(prefix):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM surveyors WHERE prefix = ?', (prefix,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return dict(zip(['id','name','prefix','status','company','address','phone','email'], result[:8]))
    return None

def get_surveyor_by_name(name):
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM surveyors WHERE name LIKE ?', (f'%{name}%',))
    result = cursor.fetchone()
    conn.close()
    if result:
        return dict(zip(['id','name','prefix','status','company','address','phone','email'], result[:8]))
    return None

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip().upper()
        if not identifier:
            flash('Please enter your name or prefix', 'error')
            return render_template('login.html')

        surveyor = get_surveyor_by_prefix(identifier) or get_surveyor_by_name(identifier)
        if surveyor:
            session['surveyor'] = surveyor
            return redirect(url_for('dashboard'))
        flash('Surveyor not found.', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    surveyor = session['surveyor']
    quarter = get_current_quarter()
    usage = get_quarterly_usage(surveyor['prefix'], quarter)
    return render_template('dashboard.html', surveyor=surveyor, quarter=quarter, usage=usage, remaining=max(0, 200 - usage))

@app.route('/generate', methods=['POST'])
def generate_beacons():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    surveyor = session['surveyor']
    quantity = int(request.form.get('quantity', 0))
    if quantity <= 0:
        flash('Invalid quantity', 'error')
        return redirect(url_for('dashboard'))

    quarter = get_current_quarter()
    usage = get_quarterly_usage(surveyor['prefix'], quarter)
    if usage + quantity > 200:
        flash(f'Quarter limit exceeded. Remaining: {200 - usage}', 'error')
        return redirect(url_for('dashboard'))

    codes = get_next_beacon_codes(quantity)
    full_codes = [f"SC/ED {code} {surveyor['prefix']}" for code in codes]

    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO beacon_logs (surveyor_prefix, surveyor_name, beacon_codes, quantity, quarter)
                      VALUES (?, ?, ?, ?, ?)''', (surveyor['prefix'], surveyor['name'], '\n'.join(full_codes), quantity, quarter))
    conn.commit()
    conn.close()

    update_quarterly_usage(surveyor['prefix'], quarter, quantity)
    return render_template('result.html', surveyor=surveyor, beacon_codes=full_codes, quantity=quantity)

@app.route('/history')
def history():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    surveyor = session['surveyor']
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT beacon_codes, quantity, generated_at, quarter FROM beacon_logs
                      WHERE surveyor_prefix = ? ORDER BY generated_at DESC''', (surveyor['prefix'],))
    logs = cursor.fetchall()
    conn.close()
    return render_template('history.html', surveyor=surveyor, logs=logs)

@app.route('/export_csv')
def export_csv():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    surveyor = session['surveyor']
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT beacon_codes, generated_at, quarter FROM beacon_logs WHERE surveyor_prefix = ?''',
                   (surveyor['prefix'],))
    logs = cursor.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Beacon Code', 'Generated At', 'Quarter'])
    for log in logs:
        for code in log[0].split('\n'):
            writer.writerow([code, log[1], log[2]])

    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=beacon_codes_{surveyor["prefix"]}.csv'})

@app.route('/logout')
def logout():
    session.pop('surveyor', None)
    return redirect(url_for('index'))

# --- App Runner ---
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
