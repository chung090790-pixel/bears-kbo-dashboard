from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / 'docs'
DATA_DIR = ROOT / 'data'
REFRESH = ROOT / 'scripts' / 'refresh.py'

app = Flask(__name__, static_folder=str(DOCS_DIR), static_url_path='')


@app.get('/')
def index():
    return send_from_directory(DOCS_DIR, 'index.html')


@app.get('/data/<path:name>')
def data_file(name: str):
    return send_from_directory(DATA_DIR, name)


@app.post('/refresh')
def refresh():
    proc = subprocess.run([sys.executable, str(REFRESH)], capture_output=True, text=True)
    latest = json.loads((DATA_DIR / 'latest.json').read_text(encoding='utf-8'))
    if proc.returncode != 0:
        return jsonify({'ok': False, 'error': proc.stderr or proc.stdout or 'refresh failed'}), 500
    return jsonify({'ok': True, 'collected_at_utc': latest['meta'].get('collected_at_utc'), 'stderr': proc.stderr})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
