from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Database setup
def init_db():
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    
    # Create surveyors table
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
    
    # Create beacon_counter table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beacon_counter (
            id INTEGER PRIMARY KEY,
            current_alpha TEXT NOT NULL DEFAULT 'AA',
            current_number INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    # Create beacon_logs table
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
    
    # Create quarterly_usage table
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
    
    # Initialize counter if not exists
    cursor.execute('SELECT COUNT(*) FROM beacon_counter')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO beacon_counter (id, current_alpha, current_number) VALUES (1, "AA", 0)')
    
    # Pre-populate surveyors from your list
    surveyors_data = [
        ("SURV. ANTHONY O. EKHATOR", "ZG", "MNIS", "TONEK SURVEYS & ENGINEERING SERVICES NIG. LTD", "6 AKPAKPAVA ROAD, OPPOSITE BEDC OFFICE, BENIN CITY", "08035003390", "toneksurveys@gmail.com"),
        ("SURV. NOSAKHARE O. IDEHEN", "ZV", "MNIS", "DITOSA FAITH SURVEYS NIG. LTD.", "NO. 6 EGUADASE ST, OFF AKPAKPAVA ROAD, BENIN CITY", "07064971629", "faith2nosa@gmail.com"),
        ("SURV. DAVID E. IMARHIAGBE", "AZ", "FNIS", "DIGITAL SURVEY CO.", "No. 7 ESIGIE ST, OFF 1ST EAST CIRCULAR ROAD, BENIN CITY", "08035510916", "davidimas4u@hotmail.com"),
        ("SURV. OLUSEGUN A. AKINSANYA", "AW", "MNIS", "AKINSEG & ASSOCIATES", "104 1ST EAST CIRCULAR ROAD, BENIN CITY", "08063397642", "akinseg16@yahoo.com"),
        ("ENGR. PROF. EHIGIATOR IRUGHE R.", "ZG", "MNIS", "GEOSYSTEMS & ENVIRONMENTAL ENGINEERING LTD.", "NO. 140, 2ND EAST CIRCULAR ROAD, BENIN CITY", "08060504291", "geosystems2004@gmail.com"),
        ("SURV. PROF. J.O. EHIOROBO", "ZV", "FNIS", "JEFFA GEOSURVEYS & TECHNICAL SERVICES LTD.", "NO.248, UGBOWO LAGOS ROAD, BENIN CITY", "08032217426", "jeffa_geos@yahoo.com"),
        ("SURV. SUBERU ANDREW OPOTU", "AY", "MNIS", "ANDY WORLD DIGITAL SURVEYS", "", "08062181439", "Opotu2000@gmail.com"),
        ("SURV. ISAAC OSAS OVU", "AX", "MNIS", "ZIKBRIDGE SURVEYS & GIS LTD", "64, URUBI STR BY OKADA HOUSE, FIVE JUNCTION, B/C", "07039597591", "zikbridgeinternational@gmail.com"),
        ("SURV. JOSEPH IGBAVBOA", "AV", "MNIS", "", "", "", ""),
        ("SURV. O.A. EDIONWE", "AU", "FNIS", "", "", "", ""),
        ("SURV. ODARO BRUNO", "AT", "MNIS", "", "", "", ""),
        ("SURV. ANDREW ANYANBINE", "AS", "MNIS", "", "", "", ""),
        ("SURV. HENRY EDIAGBONYA", "AR", "MNIS", "", "", "", ""),
        ("SURV. ONOSOHWO KENNETH SUNNY", "AQ", "MNIS", "", "", "", ""),
        ("SURV. EHIBOR OSARENREN KCEEY", "AZ", "MNIS", "", "", "", ""),
        ("SURV. CHARLES CEWUO OGIAMIEN", "AP", "MNIS", "", "", "", ""),
        ("SURV. AUGUSTINE WABINIHIA OMOROGIE", "AO", "MNIS", "", "", "", ""),
        ("SURV. THOMAS OGUNOBO", "AN", "MNIS", "", "", "", ""),
        ("SURV. ESHIEMOKHAI IYOTOR", "AM", "MNIS", "", "", "", ""),
        ("SURV. FELIX OGBEIDE", "AL", "MNIS", "", "", "", ""),
        ("SURV. J. A. OSAZUWA", "AK", "FNIS", "", "", "", ""),
        ("SURV. DR. ANDREW OLIHA", "AJ", "MNIS", "", "", "", ""),
        ("SURV. ALIU TONY PARKER", "AI", "MNIS", "", "", "", ""),
        ("SURV. J.E. ANAO", "AH", "FNIS", "", "", "", ""),
        ("SURV. AKOGUN ADEBAYO JIMOH", "AG", "MNIS", "", "", "", ""),
        ("SURV. AKUGBE GODWIN IYAMU", "AF", "MNIS", "", "", "", ""),
        ("HRH. SURV. T.U. ILOGHO", "AE", "MNIS", "", "", "", ""),
        ("SURV. ROLAND ERHABOR", "AD", "MNIS", "", "", "", ""),
        ("SURV. B.T.O. ALLO", "AC", "MNIS", "", "", "", ""),
        ("SURV. SYLVESTER ISIDAHOMEN", "AB", "MNIS", "", "", "", ""),
        ("SURV. OLATUNDE MICHAEL BANJI", "BA", "MNIS", "", "", "", ""),
        ("SURV. OSEMWOTA OSAIKHUIWU", "BB", "MNIS", "", "", "", ""),
        ("SURV. NOGHEGHASE OSAHERUN PRESLY", "BC", "MNIS", "", "", "", ""),
        ("SURV. HENRY EROMOSELE ORIAKHI", "BD", "MNIS", "", "", "", ""),
        ("SURV. MATTHEW ESEWE", "BE", "MNIS", "", "", "", ""),
        ("SURV. J.O. AMAYO", "BF", "MNIS", "", "", "", ""),
        ("SURV. D.A.S. ELUJOBADE", "BG", "MNIS", "", "", "", ""),
        ("SURV. ITOMO VICTOR", "BH", "MNIS", "", "", "", ""),
        ("SURV. AUGUSTINE AITSEBAMON", "BI", "MNIS", "", "", "", ""),
        ("SURV. ABDUL UMORU", "BJ", "MNIS", "", "", "", ""),
        ("SURV. PAUL GIWA", "BK", "MNIS", "", "", "", ""),
        ("SURV. SUNDAY OROBOSA EKHOSU", "BL", "FNIS", "", "", "", ""),
        ("SURV. FRIDAY OKEOGHENE LETTER", "BM", "MNIS", "", "", "", ""),
        ("SURV. OLATUNDE OZOFU FAITH", "BN", "MNIS", "", "", "", ""),
        ("SURV. VINCENT ONUOHA", "BO", "MNIS", "", "", "", ""),
        ("SURV. PETER OJO", "BP", "MNIS", "", "", "", ""),
        ("SURV. VICTOR OKORAFOR", "BQ", "MNIS", "", "", "", ""),
        ("SURV. DR. ODUYEBO OLUJIMI FATAI", "BR", "MNIS", "", "", "", ""),
        ("PROF. HENRY AUDU", "BS", "MNIS", "", "", "", ""),
        ("SURV. DR. DAVID AWEH", "BT", "MNIS", "", "", "", ""),
        ("SURV. THOMAS IKHAGHU", "BU", "MNIS", "", "", "", ""),
        ("SURV. DR. NWODO GEOFFREY", "AW", "MNIS", "", "", "", ""),
        ("SURV. AMADI CHIKODINAKA", "BV", "MNIS", "", "", "", "")
    ]
    
    for surveyor_data in surveyors_data:
        cursor.execute('''
            INSERT OR IGNORE INTO surveyors (name, prefix, status, company, address, phone, email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', surveyor_data)
    
    conn.commit()
    conn.close()

def get_current_quarter():
    """Get current quarter in YYYY-Q format"""
    now = datetime.now()
    quarter = (now.month - 1) // 3 + 1
    return f"{now.year}-Q{quarter}"

def get_next_beacon_codes(quantity):
    """Generate next beacon codes in sequence"""
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    
    # Get current counter
    cursor.execute('SELECT current_alpha, current_number FROM beacon_counter WHERE id = 1')
    alpha, number = cursor.fetchone()
    
    codes = []
    current_alpha = alpha
    current_number = number
    
    for _ in range(quantity):
        current_number += 1
        
        # Check if we need to rollover
        if current_number > 9999:
            current_number = 10
            # Increment alpha
            if current_alpha[1] == 'Z':
                if current_alpha[0] == 'Z':
                    # This shouldn't happen in practice
                    current_alpha = 'AA'
                else:
                    current_alpha = chr(ord(current_alpha[0]) + 1) + 'A'
            else:
                current_alpha = current_alpha[0] + chr(ord(current_alpha[1]) + 1)
        
        code = f"{current_alpha} {current_number:04d}"
        codes.append(code)
    
    # Update counter
    cursor.execute('UPDATE beacon_counter SET current_alpha = ?, current_number = ? WHERE id = 1',
                   (current_alpha, current_number))
    
    conn.commit()
    conn.close()
    
    return codes

def get_quarterly_usage(surveyor_prefix, quarter):
    """Get current quarterly usage for a surveyor"""
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT usage_count FROM quarterly_usage 
        WHERE surveyor_prefix = ? AND quarter = ?
    ''', (surveyor_prefix, quarter))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0

def update_quarterly_usage(surveyor_prefix, quarter, additional_usage):
    """Update quarterly usage for a surveyor"""
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO quarterly_usage (surveyor_prefix, quarter, usage_count)
        VALUES (?, ?, COALESCE((SELECT usage_count FROM quarterly_usage WHERE surveyor_prefix = ? AND quarter = ?), 0) + ?)
    ''', (surveyor_prefix, quarter, surveyor_prefix, quarter, additional_usage))
    
    conn.commit()
    conn.close()

def get_surveyor_by_prefix(prefix):
    """Get surveyor information by prefix"""
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM surveyors WHERE prefix = ?', (prefix,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'name': result[1],
            'prefix': result[2],
            'status': result[3],
            'company': result[4],
            'address': result[5],
            'phone': result[6],
            'email': result[7]
        }
    return None

def get_surveyor_by_name(name):
    """Get surveyor information by name"""
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM surveyors WHERE name LIKE ?', (f'%{name}%',))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'name': result[1],
            'prefix': result[2],
            'status': result[3],
            'company': result[4],
            'address': result[5],
            'phone': result[6],
            'email': result[7]
        }
    return None

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
        
        # Try to find surveyor by prefix first, then by name
        surveyor = get_surveyor_by_prefix(identifier)
        if not surveyor:
            surveyor = get_surveyor_by_name(identifier)
        
        if surveyor:
            session['surveyor'] = surveyor
            return redirect(url_for('dashboard'))
        else:
            flash('Surveyor not found. Please check your name or prefix, or contact admin for registration.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    
    surveyor = session['surveyor']
    quarter = get_current_quarter()
    usage = get_quarterly_usage(surveyor['prefix'], quarter)
    remaining = max(0, 200 - usage)
    
    return render_template('dashboard.html', 
                         surveyor=surveyor, 
                         quarter=quarter,
                         usage=usage,
                         remaining=remaining)

@app.route('/generate', methods=['POST'])
def generate_beacons():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    
    surveyor = session['surveyor']
    quantity = int(request.form.get('quantity', 0))
    
    if quantity <= 0:
        flash('Please enter a valid quantity', 'error')
        return redirect(url_for('dashboard'))
    
    quarter = get_current_quarter()
    current_usage = get_quarterly_usage(surveyor['prefix'], quarter)
    
    if current_usage + quantity > 200:
        flash(f'Request exceeds quarterly limit. You can only request {200 - current_usage} more beacons this quarter.', 'error')
        return redirect(url_for('dashboard'))
    
    # Generate beacon codes
    beacon_codes = get_next_beacon_codes(quantity)
    full_codes = [f"SC/ED {code} {surveyor['prefix']}" for code in beacon_codes]
    
    # Log the generation
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO beacon_logs (surveyor_prefix, surveyor_name, beacon_codes, quantity, quarter)
        VALUES (?, ?, ?, ?, ?)
    ''', (surveyor['prefix'], surveyor['name'], '\n'.join(full_codes), quantity, quarter))
    conn.commit()
    conn.close()
    
    # Update quarterly usage
    update_quarterly_usage(surveyor['prefix'], quarter, quantity)
    
    return render_template('result.html', 
                         surveyor=surveyor,
                         beacon_codes=full_codes,
                         quantity=quantity)

@app.route('/history')
def history():
    if 'surveyor' not in session:
        return redirect(url_for('login'))
    
    surveyor = session['surveyor']
    
    conn = sqlite3.connect('beacongen.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT beacon_codes, quantity, generated_at, quarter 
        FROM beacon_logs 
        WHERE surveyor_prefix = ? 
        ORDER BY generated_at DESC
    ''', (surveyor['prefix'],))
    
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
    cursor.execute('''
        SELECT beacon_codes, quantity, generated_at, quarter 
        FROM beacon_logs 
        WHERE surveyor_prefix = ? 
        ORDER BY generated_at DESC
    ''', (surveyor['prefix'],))
    
    logs = cursor.fetchall()
    conn.close()
    
    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Beacon Code', 'Generated At', 'Quarter'])
    
    for log in logs:
        beacon_codes = log[0].split('\n')
        generated_at = log[2]
        quarter = log[3]
        
        for code in beacon_codes:
            writer.writerow([code, generated_at, quarter])
    
    csv_content = output.getvalue()
    output.close()
    
    from flask import Response
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=beacon_codes_{surveyor["prefix"]}.csv'}
    )

@app.route('/logout')
def logout():
    session.pop('surveyor', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
