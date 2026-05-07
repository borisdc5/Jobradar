"""
Weekly job: fetches all companies from RecruitCRM and writes crm_cache.json.
Run via GitHub Actions every Sunday, or manually:
  RECRUITCRM_API_KEY=xxx python3 build_crm_cache.py
"""
import urllib.request, urllib.parse, ssl, json, os, time
from datetime import datetime, timezone

TOKEN = os.getenv('RECRUITCRM_API_KEY', '')
BASE  = 'https://api.recruitcrm.io/v1'
RCRM_APP = 'https://app.recruitcrm.io/v1/company'
OUT   = os.path.join(os.path.dirname(__file__), 'crm_cache.json')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode    = ssl.CERT_NONE

def rcrm_get(path, params=None):
    url = BASE + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json',
        'User-Agent': 'JobRadar/1.0',
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f'  Erreur API: {e}')
        return None

if not TOKEN:
    print('RECRUITCRM_API_KEY absent — abandon')
    exit(1)

print('Chargement de toutes les entreprises RecruitCRM...')
companies = {}
page = 1
consecutive_errors = 0

while True:
    data = rcrm_get('/companies', {'per_page': 100, 'page': page})
    if not data:
        consecutive_errors += 1
        if consecutive_errors >= 3:
            print(f'  3 erreurs consécutives — arrêt à la page {page}')
            break
        time.sleep(2)
        continue
    consecutive_errors = 0

    items = data.get('data', [])
    if not items:
        break

    for c in items:
        name = (c.get('company_name') or '').strip()
        if not name:
            continue
        slug = c.get('slug') or str(c.get('id') or '')
        crm_link = f'{RCRM_APP}/{slug}' if slug else ''

        # Status from custom_fields
        status = ''
        for cf in c.get('custom_fields', []):
            if cf.get('field_name') == 'Company Status':
                status = (cf.get('value') or '').strip()
                break

        companies[name.lower()] = {
            'company_name': name,
            'crm_link':     crm_link,
            'status':       status,
            'is_client':    status == 'Active Account',
        }

    print(f'  Page {page:3d} → {len(items)} entrées (total {len(companies)})')

    if len(items) < 100:
        break

    page += 1
    # Respect 60 req/min rate limit: ~1s between pages is safe
    time.sleep(1.1)

cache = {
    'updated':   datetime.now(timezone.utc).isoformat(),
    'total':     len(companies),
    'companies': companies,
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, separators=(',', ':'))

clients  = sum(1 for v in companies.values() if v['is_client'])
prospect = sum(1 for v in companies.values() if v['status'] == 'Prospect')
print(f'\nCache écrit : {len(companies)} entreprises '
      f'({clients} clients actifs, {prospect} prospects)')
print(f'Fichier : {OUT}')
