@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    codes = []
    show_add_form = False
    missing_prefix = ''

    if request.method == 'POST':
        prefix = request.form.get('prefix')
        qty = request.form.get('quantity')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM surveyors WHERE prefix = ?", (prefix,))
        row = c.fetchone()
        conn.close()

        if not row:
            # Surveyor not found, prompt to add
            show_add_form = True
            missing_prefix = prefix
        else:
            # Surveyor exists, generate beacons
            message, codes = generate_beacons(prefix, int(qty))

    return render_template('index.html', message=message, codes=codes, show_add_form=show_add_form, missing_prefix=missing_prefix)
@app.route('/add_surveyor', methods=['POST'])
def handle_add_surveyor():
    name = request.form['name']
    prefix = request.form['prefix']

    add_surveyor(name, prefix)
    return render_template('index.html', message=f"Surveyor {name} added. You can now request beacons.", codes=[], show_add_form=False)
