import csv
import re
from pathlib import Path

BASE_DIR = Path('.')
CSV_FILE = BASE_DIR / 'data' / 'processed' / 'adobe_stock_upload.csv'
IMAGES_DIR = BASE_DIR / 'data' / 'final' / 'images'

def sanitize(t):
    n = re.sub(r'[^a-z0-9\s-]', '', t.lower())
    n = re.sub(r'[\s-]+', '-', n).strip('-')
    return n[:60].rsplit('-', 1)[0] if len(n) > 60 else n

if not CSV_FILE.exists():
    print('No CSV found')
    exit()

rows = []
with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        old_name = row['Filename']
        old_path = IMAGES_DIR / old_name
        if old_path.exists():
            base = sanitize(row['Title']) or 'stock-image'
            new_path = old_path.with_name(f'{base}.jpg')
            c = 1
            while new_path.exists() and new_path != old_path:
                new_path = old_path.with_name(f'{base}-{c}.jpg')
                c += 1
            old_path.rename(new_path)
            row['Filename'] = new_path.name
            print(f'Renamed: {old_name} -> {new_path.name}')
        rows.append(row)

with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['Filename','Title','Keywords','Category','Releases'])
    w.writeheader()
    w.writerows(rows)
print('Done!')
