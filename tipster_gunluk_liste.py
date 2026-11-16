"""TIPSTER PRO - Kilitli V4 tahminlerinden bugun/yarin okunabilir liste.

Girdi: tipster_v4_kilitli_arsiv.json
Ciktilar: tipster_bugun_tahminleri.txt, tipster_yarin_tahminleri.txt
          tipster_gunluk_ozet.json
Yalnizca okur; tahminleri ve kilitli arsivi DEGISTIRMEZ.
Saat/tarih siniri: Europe/London.
"""
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ARCHIVE = Path('tipster_v4_kilitli_arsiv.json')
LONDON = ZoneInfo('Europe/London')
OUTPUTS = (
    ('bugun', Path('tipster_bugun_tahminleri.txt')),
    ('yarin', Path('tipster_yarin_tahminleri.txt')),
)
SUMMARY = Path('tipster_gunluk_ozet.json')


def parse_utc(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def text_value(value):
    return ' '.join(str(value or '').replace('|', '/').split())


def extract_matches(archive):
    records = archive.get('records') if isinstance(archive, dict) else None
    if not isinstance(records, dict):
        raise ValueError('Kilitli arÅivde records sÃ¶zlÃ¼ÄÃ¼ bulunamadÄ±; iÅlem durduruldu.')
    matches = []
    for key, p in records.items():
        if not isinstance(p, dict):
            continue
        kickoff = parse_utc(p.get('tarih'))
        if kickoff is None:
            continue
        v4 = p.get('v4') if isinstance(p.get('v4'), dict) else {}
        locked_at = parse_utc(p.get('kilit_zamani') or p.get('v4_created_at_utc'))
        # Inaccurate/missing timestamp is reported as 'KILIT ZAMANI KONTROL' rather than confirmed.
        status = ('ONCEDEN KILITLI' if locked_at and locked_at < kickoff
                  else 'KILIT ZAMANI KONTROL')
        matches.append({
            'key': key,
            'kickoff': kickoff,
            'home': text_value(p.get('ev') or p.get('ev_sahibi')),
            'away': text_value(p.get('dep') or p.get('deplasman')),
            'league': text_value(p.get('lig')),
            'over': text_value(p.get('karar') or v4.get('ust_karari') or 'KARAR YOK'),
            'btts': text_value(v4.get('gol_var_yok_karari') or p.get('gol_var_yok_karari') or 'KARAR YOK'),
            'status': status,
        })
    return matches


def make_day(matches, day, name, path, generated_at):
    selected = sorted(
        (p for p in matches if p['kickoff'].astimezone(LONDON).date() == day),
        key=lambda p: (p['kickoff'], p['league'], p['home']),
    )
    counts = Counter(x['over'] for x in selected)
    lines = [
        f'TIPSTER PRO V4 - {name.upper()} TAHMINLERI',
        f'Tarih (Londra): {day.isoformat()}',
        f'Rapor olusturulma (UTC): {generated_at.isoformat()}',
        f'Kilitli arsivden okunan mac: {len(selected)}',
        'Bu bir mac oncesi kilitli tahmin listesidir; basari raporu degildir.',
        '',
        'SAAT (LONDRA) | LIG | MAC | UST TAHMINI | GOL VAR/YOK | KILIT DURUMU',
        '-' * 112,
    ]
    for p in selected:
        local = p['kickoff'].astimezone(LONDON)
        lines.append(' | '.join((local.strftime('%H:%M'), p['league'],
                                 f"{p['home']} - {p['away']}", p['over'], p['btts'], p['status'])))
    if not selected:
        lines.append('Bu tarih icin kilitli arsivde mac bulunamadi.')
    lines += ['', 'TAHMIN DAGILIMI:']
    lines += [f'{k}: {v}' for k, v in sorted(counts.items())]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'date_london': day.isoformat(), 'matches': len(selected), 'counts': dict(counts),
            'filename': str(path)}


def main():
    if not ARCHIVE.exists():
        raise FileNotFoundError('tipster_v4_kilitli_arsiv.json bulunamadi')
    data = json.loads(ARCHIVE.read_text(encoding='utf-8'))
    matches = extract_matches(data)
    now = datetime.now(timezone.utc)
    today = now.astimezone(LONDON).date()
    days = (today, today + timedelta(days=1))
    output = [make_day(matches, d, label, path, now)
              for (label, path), d in zip(OUTPUTS, days)]
    SUMMARY.write_text(json.dumps({'created_at_utc': now.isoformat(), 'reports': output},
                                  ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for result in output:
        print(f"{result['date_london']} | mac: {result['matches']} | {result['filename']}")
    print('Ozet:', SUMMARY)


if __name__ == '__main__':
    main()
