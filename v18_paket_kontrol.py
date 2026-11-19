#!/usr/bin/env python3
"""V18 integration preflight: read-only local checks, no ESPN calls or file edits."""
import ast
import json
import sys
from pathlib import Path
from fikstur_yeni import LIGLER
from v18_sonuc_takip import ayarlar_oku, kimlik, utc

ROOT = Path(__file__).resolve().parent
REQUIRED = [
    '.github/workflows/v18-canli-tahmin-ve-pages.yml',
    'gercek_tahmin_v18.py', 'fikstur_yeni.py', 'v18_panel_aktar.py',
    'v18_sonuc_takip.py', 'v18_sonuc_ayarlari.json', 'test_v18_sonuc_takip.py',
    'v18_tahmin_arsivi.json', 'index.html', 'panel.js', 'panel.css',
]


def main():
    missing = [name for name in REQUIRED if not (ROOT/name).is_file()]
    if missing:
        raise SystemExit('EKSIK KRITIK DOSYA: ' + ', '.join(missing))
    for path in ROOT.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    ayarlar_oku()
    archive = json.loads((ROOT/'v18_tahmin_arsivi.json').read_text(encoding='utf-8'))
    if not isinstance(archive, list):
        raise SystemExit('Arsiv liste degil')
    seen = set()
    for record in archive:
        match = record.get('mac',{})
        identifier = kimlik(match)
        if not identifier or identifier != record.get('kimlik') or identifier in seen:
            raise SystemExit('GECERSIZ / TEKRARLAYAN ARSIV KIMLIGI: ' + str(identifier))
        if utc(match.get('tarih')) is None:
            raise SystemExit('UTC baslangic gecersiz: ' + identifier)
        seen.add(identifier)
    print('PREFLIGHT OK')
    print('ESPN tanimli lig:',len(LIGLER))
    print('Arsiv kaydi:',len(archive))
    print('Python modul:',len(list(ROOT.glob('*.py'))))
    print('Not: Bu test canli ESPN erisimi veya GitHub Pages yayini kanitlamaz.')


if __name__ == '__main__':
    main()
