import urllib.request, urllib.parse, ssl, json, re, os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

AFJV_RSS = 'https://emploi.afjv.com/rss.xml'
FT_TOKEN_URL = 'https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire'
FT_API_URL   = 'https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search'

FT_CLIENT_ID     = os.getenv('FT_CLIENT_ID', '')
FT_CLIENT_SECRET = os.getenv('FT_CLIENT_SECRET', '')

ESN = ['capgemini','atos','sopra','accenture','michael page','hays','robert half','manpower',
       'adecco','randstad','sqli','altran','alten','aubay','devoteam','wavestone','kpmg',
       'deloitte','pwc','umaneer','experis','modis','itekway','alteca','informatis',
       'start people','groupe open']

def is_esn(company):
    c = (company or '').lower()
    return any(e in c for e in ESN)

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, context=ctx, timeout=20).read()

def days_ago(date_str):
    try:
        from email.utils import parsedate_to_datetime
        d = parsedate_to_datetime(date_str)
    except Exception:
        try:
            d = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return 99
    return max(0, (datetime.now(timezone.utc) - d).days)

# ── AFJV ──────────────────────────────────────────────────────────────────────

def afjv_company(desc):
    m = re.match(r'^(.+?)\s+recrute', desc, re.IGNORECASE)
    return m.group(1).strip() if m else 'Studio'

def afjv_location(desc):
    m = re.search(r'bas[eé]\s+[aà]\s+([^(]+)\s*\((\d{2,3})\)', desc, re.IGNORECASE)
    if not m: return 'France'
    city, dept = m.group(1).strip().lower(), m.group(2)
    if dept == '00' or any(x in city for x in ['teletravail','télétravail','remote']): return 'Remote'
    if dept in ['75','92','93','94','95','77','78','91'] or any(x in city for x in ['paris','boulogne','nanterre','montrouge','issy','cergy']): return 'Paris'
    if dept == '69' or any(x in city for x in ['lyon','villeurbanne']): return 'Lyon'
    if dept == '33' or 'bordeaux' in city: return 'Bordeaux'
    if dept == '35' or 'rennes' in city: return 'Rennes'
    if dept == '44' or 'nantes' in city: return 'Nantes'
    if dept == '34' or 'montpellier' in city: return 'Montpellier'
    if dept == '31' or 'toulouse' in city: return 'Toulouse'
    if dept == '59' or any(x in city for x in ['lille','valenciennes']): return 'Lille'
    if dept == '13' or any(x in city for x in ['marseille','aix']): return 'Marseille'
    return m.group(1).strip()

def parse_afjv(xml):
    jobs = []
    for i, item in enumerate(re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)):
        def g(tag, _item=item):
            m = re.search(r'<'+tag+r'[^>]*>(.*?)</'+tag+r'>', _item, re.DOTALL)
            return m.group(1).strip() if m else ''
        cats = re.findall(r'<category>(.*?)</category>', item)
        contrat = next((c for c in cats if c in ['CDI','CDD','Stage','Alternance','Freelance','Intermittent']), '')
        if contrat != 'CDI': continue
        category = next((c for c in cats if c not in ['CDI','CDD','Stage','Alternance','Freelance','Intermittent','France','International','Belgique']), '')
        desc = re.sub(r'<[^>]+>', ' ', g('description')).strip()
        company = afjv_company(desc)
        jobs.append({'id': i, 'title': g('title'), 'company': company, 'link': g('link'),
                     'desc': desc[:200], 'location': afjv_location(desc), 'category': category,
                     'daysAgo': days_ago(g('pubDate')), 'isESN': is_esn(company), 'source': 'afjv'})
    return jobs

# ── France Travail API ─────────────────────────────────────────────────────────

def ft_get_token():
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': FT_CLIENT_ID,
        'client_secret': FT_CLIENT_SECRET,
        'scope': 'api_offresdemploiv2 o2dsoffre',
    }).encode()
    req = urllib.request.Request(FT_TOKEN_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    return json.loads(urllib.request.urlopen(req, context=ctx, timeout=15).read())['access_token']

def ft_normalize_location(lieu):
    raw = lieu.get('libelle', '')
    parts = raw.split(' - ', 1)
    dept = parts[0].strip()
    city = parts[1].strip().lower() if len(parts) == 2 else raw.lower()
    if any(x in city for x in ['remote','teletravail','télétravail']): return 'Remote'
    if dept in ['75','92','93','94','95','77','78','91'] or any(x in city for x in ['paris','boulogne','nanterre','montrouge','issy','cergy']): return 'Paris'
    if dept == '69' or any(x in city for x in ['lyon','villeurbanne']): return 'Lyon'
    if dept == '33' or 'bordeaux' in city: return 'Bordeaux'
    if dept == '35' or 'rennes' in city: return 'Rennes'
    if dept == '44' or 'nantes' in city: return 'Nantes'
    if dept == '34' or 'montpellier' in city: return 'Montpellier'
    if dept == '31' or 'toulouse' in city: return 'Toulouse'
    if dept == '59' or any(x in city for x in ['lille','valenciennes']): return 'Lille'
    if dept == '13' or any(x in city for x in ['marseille','aix']): return 'Marseille'
    if dept == '67' or 'strasbourg' in city: return 'Strasbourg'
    if dept == '06' or 'nice' in city: return 'Nice'
    return parts[1].strip() if len(parts) == 2 else raw.strip()

def ft_category(title, rome):
    t = (title + ' ' + rome).lower()
    if any(x in t for x in ['data','machine learning','intelligence artificielle',' ia ','analyst','business intel','big data','dataops','mlops']): return 'Data / Gestion de données'
    if any(x in t for x in ['développeur','développeuse','software','fullstack','full-stack','front','back','mobile','python','java','.net','php','react','angular','programmeur','ingénieur logiciel']): return 'Programmation'
    if any(x in t for x in ['devops','cloud','infrastructure','sre','système','réseau','administrateur sys','ops','kubernetes','docker','ansible']): return 'DevOps / Cloud'
    if any(x in t for x in ['cybersécurité','cyber sécurité','sécurité informatique','rssi','pentest','soc ','vulnerability']): return 'Cybersécurité'
    if any(x in t for x in ['product manager','product owner',' po ','chef de projet','scrum','agile','program manager','project manager']): return 'Product / Projet'
    if any(x in t for x in ['ux','ui ','designer','design','expérience utilisateur','ergonome']): return 'UX / Design'
    if any(x in t for x in ['test','qa ','qualité logiciel','recette','assurance qualité']): return 'Test / QA'
    if any(x in t for x in ['manager','management','directeur','responsable','dsi','cto','cio','head of']): return 'Management'
    if any(x in t for x in ['commercial','marketing','vente','business dev','account manager','growth']): return 'Commercial / Marketing'
    return ''

FT_KEYWORDS = [
    'développeur',
    'devops',
    'cloud',
    'data',
    'cybersécurité',
    'product manager',
]

def fetch_ft():
    if not FT_CLIENT_ID or not FT_CLIENT_SECRET:
        print('  Credentials FT absents, ignoré')
        return []
    token = ft_get_token()
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    seen, jobs = set(), []
    for kw in FT_KEYWORDS:
        enc = urllib.parse.quote(kw)
        url = f'{FT_API_URL}?typeContrat=CDI&motsCles={enc}&range=0-149'
        req = urllib.request.Request(url, headers=headers)
        try:
            data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=20).read())
        except Exception as e:
            print(f'  [{kw}] erreur: {e}')
            continue
        for o in data.get('resultats', []):
            job_id = o.get('id', '')
            if job_id in seen:
                continue
            company = (o.get('entreprise') or {}).get('nom', '').strip()
            if not company:
                continue
            seen.add(job_id)
            title = o.get('intitule', '')
            jobs.append({
                'id': 200000 + len(jobs),
                'title': title,
                'company': company,
                'link': (o.get('origineOffre') or {}).get('urlOrigine', '#'),
                'desc': o.get('description', '')[:200],
                'location': ft_normalize_location(o.get('lieuTravail') or {}),
                'category': ft_category(title, o.get('romeLibelle', '')),
                'daysAgo': days_ago(o.get('dateCreation', '')),
                'isESN': is_esn(company),
                'source': 'ft',
            })
        print(f'  [{kw}] +{len(data.get("resultats",[]))} → {len(jobs)} uniques')
    return jobs

# ── Sport Jobs Hunter ─────────────────────────────────────────────────────────

SJH_RSS = 'https://www.sportjobshunter.com/?feed=job_feed&job_types=cdi&posts_per_page=100'

def parse_sjh(xml):
    jobs = []
    for i, item in enumerate(re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)):
        def g(tag, _item=item):
            m = re.search(r'<' + tag + r'[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</' + tag + r'>', _item, re.DOTALL)
            return m.group(1).strip() if m else ''
        title   = g('title')
        company = g('job_listing:company')
        location_raw = g('job_listing:location')
        link    = g('link')
        pub     = g('pubDate')
        if not company:
            continue
        # Normalize location — format "City, France" or "City, Country"
        city = location_raw.split(',')[0].strip()
        jobs.append({
            'id': 400000 + i,
            'title': title,
            'company': company,
            'link': link,
            'desc': '',
            'location': ms_normalize_location(city, '') if city else 'France',
            'category': '',
            'daysAgo': days_ago(pub),
            'isESN': is_esn(company),
            'source': 'sjh',
        })
    return jobs

# ── Makesense ─────────────────────────────────────────────────────────────────

MS_SITEMAP = 'https://jobs.makesense.org/sitemap-jobs.xml'

def ms_normalize_location(city, postal):
    c, d = city.lower(), postal[:2] if postal else ''
    if any(x in c for x in ['remote','télétravail','teletravail']): return 'Remote'
    if d in ['75','92','93','94','95','77','78','91'] or any(x in c for x in ['paris','nanterre','boulogne','montrouge','issy','cergy']): return 'Paris'
    if d == '69' or any(x in c for x in ['lyon','villeurbanne']): return 'Lyon'
    if d == '33' or 'bordeaux' in c: return 'Bordeaux'
    if d == '35' or 'rennes' in c: return 'Rennes'
    if d == '44' or 'nantes' in c: return 'Nantes'
    if d == '34' or 'montpellier' in c: return 'Montpellier'
    if d == '31' or 'toulouse' in c: return 'Toulouse'
    if d == '59' or any(x in c for x in ['lille','valenciennes']): return 'Lille'
    if d == '13' or any(x in c for x in ['marseille','aix']): return 'Marseille'
    if d == '67' or 'strasbourg' in c: return 'Strasbourg'
    return city.strip() or 'France'

def _fetch_ms_job(args):
    idx, url = args
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8', 'replace')
        scripts = re.findall(r'application/ld\+json[^>]*>([\s\S]*?)</script>', html)
        if not scripts:
            return None
        d = json.loads(scripts[0])
        if d.get('@type') != 'JobPosting':
            return None
        company = (d.get('hiringOrganization') or {}).get('name', '').strip()
        if not company:
            return None
        title = d.get('title', '')
        loc_data = d.get('jobLocation', [{}])
        if isinstance(loc_data, dict):
            loc_data = [loc_data]
        addr = (loc_data[0] if loc_data else {}).get('address', {})
        location = ms_normalize_location(addr.get('addressLocality', ''), addr.get('postalCode', ''))
        date_posted = d.get('datePosted', '')
        try:
            dp = datetime.fromisoformat(date_posted)
            if dp.tzinfo is None:
                dp = dp.replace(tzinfo=timezone.utc)
            age = max(0, (datetime.now(timezone.utc) - dp).days)
        except Exception:
            age = 99
        desc = re.sub(r'<[^>]+>', ' ', d.get('description', '')).strip()[:200]
        return {
            'id': 300000 + idx,
            'title': title,
            'company': company,
            'link': url,
            'desc': desc,
            'location': location,
            'category': ft_category(title, ''),
            'daysAgo': age,
            'isESN': is_esn(company),
            'source': 'ms',
        }
    except Exception:
        return None

def fetch_makesense(max_jobs=200):
    req = urllib.request.Request(MS_SITEMAP, headers={'User-Agent': 'Mozilla/5.0'})
    xml = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode()
    entries = re.findall(r'<loc>(https://jobs\.makesense\.org/fr/jobs/[^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', xml)
    entries.sort(key=lambda x: x[1], reverse=True)
    entries = entries[:max_jobs]
    jobs = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_ms_job, (i, url)): i for i, (url, _) in enumerate(entries)}
        for future in as_completed(futures):
            result = future.result()
            if result:
                jobs.append(result)
    return sorted(jobs, key=lambda j: j['daysAgo'])

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    jobs = []

    print('Fetch AFJV...')
    try:
        afjv = parse_afjv(http_get(AFJV_RSS).decode('utf-8'))
        jobs += afjv
        print(f'  {len(afjv)} CDI AFJV')
    except Exception as e:
        print(f'  AFJV erreur: {e}')

    print('Fetch France Travail API...')
    try:
        ft = fetch_ft()
        jobs += ft
        print(f'  {len(ft)} CDI France Travail')
    except Exception as e:
        print(f'  France Travail erreur: {e}')

    print('Fetch Sport Jobs Hunter...')
    try:
        sjh = parse_sjh(http_get(SJH_RSS).decode('utf-8'))
        jobs += sjh
        print(f'  {len(sjh)} CDI Sport Jobs Hunter')
    except Exception as e:
        print(f'  Sport Jobs Hunter erreur: {e}')

    print('Fetch Makesense...')
    try:
        ms = fetch_makesense(max_jobs=200)
        jobs += ms
        print(f'  {len(ms)} offres Makesense')
    except Exception as e:
        print(f'  Makesense erreur: {e}')

    print(f'Total: {len(jobs)} offres')
    updated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    template = open('template.html', encoding='utf-8').read()
    html = (template
            .replace('__JOBS__', json.dumps(jobs, ensure_ascii=False))
            .replace('"__UPDATED__"', f'"{updated}"'))

    os.makedirs('docs', exist_ok=True)
    open('docs/index.html', 'w', encoding='utf-8').write(html)
    print('docs/index.html généré')
