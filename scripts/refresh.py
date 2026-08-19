from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
LATEST_JSON = DATA_DIR / 'latest.json'
BACKUP_JSON = DATA_DIR / 'latest.lastgood.json'
TIMEOUT = 20
RETRIES = 3
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; BearsDashboardBot/1.0; +https://github.com/)'
}
TEAM_RANK_URL = 'https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx'
TEAM_HITTER_URL = 'https://www.koreabaseball.com/Record/Team/Hitter/Basic1.aspx'
TEAM_PITCHER_URL = 'https://www.koreabaseball.com/Record/Team/Pitcher/Basic1.aspx'
PLAYER_URLS = {
    '곽빈': 'https://web1.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId=68220',
    '벤자민': 'https://web1.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId=52043',
    '최민석': 'https://web1.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId=55268',
    '잭로그': 'https://web1.koreabaseball.com/Record/Player/PitcherDetail/Basic.aspx?playerId=55239',
}


def fetch_text(session: requests.Session, url: str) -> str:
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            res = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            res.raise_for_status()
            return res.text
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < RETRIES:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f'fetch failed for {url}: {last_err}')


def normalize_space(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def parse_team_summary(rank_html: str, hitter_html: str, pitcher_html: str) -> Dict[str, Any]:
    def find_doosan_row(html_text: str) -> list[str]:
        soup = BeautifulSoup(html_text, 'html.parser')
        for tr in soup.select('tr'):
            cells = [normalize_space(td.get_text(' ', strip=True)) for td in tr.select('th,td')]
            if any('두산' == c or '두산 베어스' in c for c in cells):
                return cells
        raise RuntimeError('Doosan row not found')

    rank_cells = find_doosan_row(rank_html)
    hitter_cells = find_doosan_row(hitter_html)
    pitcher_cells = find_doosan_row(pitcher_html)

    def extract_record(cells: list[str]) -> Optional[str]:
        for i, cell in enumerate(cells):
            if re.fullmatch(r'\d+', cell) and i + 2 < len(cells):
                maybe = '-'.join(cells[i:i+3])
                if re.fullmatch(r'\d+-\d+-\d+', maybe):
                    return maybe
        return None

    record = extract_record(rank_cells)

    def first_float(cells: list[str], pattern: str) -> Optional[float]:
        rx = re.compile(pattern)
        for c in cells:
            if rx.fullmatch(c):
                try:
                    return float(c)
                except ValueError:
                    pass
        return None

    rank = None
    for c in rank_cells:
        if c.isdigit():
            rank = int(c)
            break

    return {
        'rank': rank,
        'record': record,
        'win_pct': first_float(rank_cells, r'0\.\d+'),
        'games_back': first_float(rank_cells, r'\d+(?:\.\d+)?'),
        'team_avg': first_float(hitter_cells, r'0\.\d+'),
        'team_era': first_float(pitcher_cells, r'\d+\.\d+'),
        'team_whip': None,
        'team_runs': None,
        'team_hits': None,
        'team_so': None,
    }


def parse_pitcher_basic(html_text: str, fallback_name: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text('\n', strip=True)

    def grab(label: str, pattern: str = r'([0-9]+(?:\.[0-9]+)?(?:\s[0-9]/[0-9])?)'):
        m = re.search(label + r'.{0,40}?' + pattern, text)
        return m.group(1) if m else None

    return {
        'name': fallback_name,
        'era': grab('ERA'),
        'g': grab(r'G'),
        'w': grab(r'W'),
        'l': grab(r'L'),
        'ip': grab('IP'),
        'h': grab(r'H'),
        'hr': grab('HR'),
        'bb': grab('BB'),
        'hbp': None,
        'so': grab('SO'),
        'r': grab(r'R'),
        'er': grab(r'ER'),
        'whip': grab('WHIP'),
    }


def load_last_good() -> Dict[str, Any]:
    if BACKUP_JSON.exists():
        return json.loads(BACKUP_JSON.read_text(encoding='utf-8'))
    if LATEST_JSON.exists():
        return json.loads(LATEST_JSON.read_text(encoding='utf-8'))
    raise FileNotFoundError('no last good JSON available')


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    try:
        rank_html = fetch_text(session, TEAM_RANK_URL)
        hitter_html = fetch_text(session, TEAM_HITTER_URL)
        pitcher_html = fetch_text(session, TEAM_PITCHER_URL)
        summary = parse_team_summary(rank_html, hitter_html, pitcher_html)
        rotation = []
        for name, url in PLAYER_URLS.items():
            player_html = fetch_text(session, url)
            parsed = parse_pitcher_basic(player_html, name)
            parsed.update({'player_id': url.split('playerId=')[-1], 'source': url})
            rotation.append(parsed)

        latest = load_last_good()
        latest['meta']['collected_at_utc'] = datetime.now(timezone.utc).isoformat()
        latest['sources'] = {
            'team_rank': TEAM_RANK_URL,
            'team_hitter': TEAM_HITTER_URL,
            'team_pitcher': TEAM_PITCHER_URL,
        }
        latest['summary'].update({k: v for k, v in summary.items() if v is not None})
        by_name = {p['name']: p for p in latest['rotation']}
        for parsed in rotation:
            if parsed['name'] in by_name:
                by_name[parsed['name']].update(parsed)

        temp_path = Path(tempfile.mkstemp(prefix='bears_', suffix='.json')[1])
        temp_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding='utf-8')
        shutil.copy2(temp_path, BACKUP_JSON)
        shutil.move(str(temp_path), LATEST_JSON)
        return 0
    except Exception as exc:  # noqa: BLE001
        last_good = load_last_good()
        fallback_payload = dict(last_good)
        fallback_payload.setdefault('meta', {})['last_refresh_error'] = str(exc)
        LATEST_JSON.write_text(json.dumps(fallback_payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'WARNING: refresh failed, kept last good JSON: {exc}', file=sys.stderr)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
