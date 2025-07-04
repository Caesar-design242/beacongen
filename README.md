# Beacon Classification System

A web-based survey beacon number classification and validation system built with Flask and SQLite.

## Features

- Login with name or prefix
- Generate beacon numbers (SC/ED format)
- View history and export CSV
- Enforces quarterly usage limits

## Tech Stack

- Flask (Backend)
- SQLite (Development DB)
- QGIS/PostGIS (Spatial Analysis)
- TailwindCSS + Bootstrap (Frontend)
- Python libraries: GeoPandas, Shapely (optional in analysis)

## Run Locally

```bash
git clone https://github.com/yourusername/beacon-classification-system.git
cd beacon-classification-system
pip install -r requirements.txt
python app.py
