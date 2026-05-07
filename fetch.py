import urllib.request, urllib.parse, ssl, json, re, os, gzip, http.cookiejar
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
APEC_EMAIL       = os.getenv('APEC_EMAIL', '')
APEC_PASSWORD    = os.getenv('APEC_PASSWORD', '')
RECRUITCRM_TOKEN = os.getenv('RECRUITCRM_API_KEY', '')

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

SJH_RSS  = 'https://www.sportjobshunter.com/?feed=job_feed&job_types=cdi&posts_per_page=100'
HW_BASE  = 'https://www.hellowork.com'
HW_SEARCH = HW_BASE + '/fr-fr/emploi/recherche.html'
LIR_BASE  = 'https://www.lindustrie-recrute.fr'
LIR_SEARCH = LIR_BASE + '/candidat/recherche/?contract_types%5B%5D=1&salary_min=0&distance=5&query_string=%22informatique%22&sort=date%7Cdesc'

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

# ── HelloWork ─────────────────────────────────────────────────────────────────

HW_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.5',
}

def _fetch_hw_job(args):
    idx, job_id = args
    url = f'{HW_BASE}/fr-fr/emplois/{job_id}.html'
    try:
        req = urllib.request.Request(url, headers=HW_HEADERS)
        html = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode('utf-8', 'replace')
        scripts = re.findall(r'application/ld\+json[^>]*>([\s\S]*?)</script>', html)
        for raw in scripts:
            try:
                d = json.loads(raw)
            except Exception:
                continue
            if d.get('@type') != 'JobPosting':
                continue
            if d.get('employmentType') not in ('FULL_TIME', 'CDI'):
                return None
            company = (d.get('hiringOrganization') or {}).get('name', '').strip()
            if not company:
                return None
            title = d.get('title', '')
            loc_data = d.get('jobLocation', {})
            if isinstance(loc_data, list):
                loc_data = loc_data[0] if loc_data else {}
            addr = loc_data.get('address', {})
            city   = addr.get('addressLocality', '')
            postal = addr.get('postalCode', '')
            location = ms_normalize_location(city, postal)
            date_posted = d.get('datePosted', '')
            try:
                dp = datetime.fromisoformat(date_posted.replace('Z', '+00:00'))
                if dp.tzinfo is None:
                    dp = dp.replace(tzinfo=timezone.utc)
                age = max(0, (datetime.now(timezone.utc) - dp).days)
            except Exception:
                age = 99
            desc = re.sub(r'<[^>]+>', ' ', d.get('description', '')).strip()[:200]
            return {
                'id': 500000 + idx,
                'title': title,
                'company': company,
                'link': url,
                'desc': desc,
                'location': location,
                'category': ft_category(title, ''),
                'daysAgo': age,
                'isESN': is_esn(company),
                'source': 'hw',
            }
    except Exception:
        pass
    return None

HW_KEYWORDS = [
    'développeur',
    'data',
    'devops',
    'cloud',
    'cybersécurité',
    'product manager',
    'designer',
    'ingénieur logiciel',
]

def fetch_hellowork(pages_per_kw=2):
    seen_ids = []
    for kw in HW_KEYWORDS:
        enc = urllib.parse.quote(kw)
        for p in range(1, pages_per_kw + 1):
            url = f'{HW_SEARCH}?k={enc}&c=CDI&p={p}'
            try:
                req = urllib.request.Request(url, headers=HW_HEADERS)
                html = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode('utf-8', 'replace')
                ids = re.findall(r'/fr-fr/emplois/(\d+)\.html', html)
                new = [jid for jid in ids if jid not in seen_ids]
                seen_ids += new
            except Exception as e:
                print(f'  [HW {kw} p{p}] erreur: {e}')
        print(f'  [HW] "{kw}" → {len(seen_ids)} IDs uniques cumulés')
    jobs = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_fetch_hw_job, (i, jid)): jid for i, jid in enumerate(seen_ids)}
        for future in as_completed(futures):
            result = future.result()
            if result:
                jobs.append(result)
    return sorted(jobs, key=lambda j: j['daysAgo'])

# ── L'Industrie Recrute ───────────────────────────────────────────────────────

def lir_parse_age(text):
    """Convert 'il y a X jours/semaines/heures' to integer days."""
    t = text.lower().strip()
    if any(x in t for x in ['aujourd', 'heure', 'minute']): return 0
    m = re.search(r'il y a (\d+)\s*(jour|semaine|mois)', t)
    if not m: return 99
    n = int(m.group(1))
    unit = m.group(2)
    if 'semaine' in unit: return n * 7
    if 'mois' in unit: return n * 30
    return n

def fetch_lir(max_pages=6):
    jobs, seen_ids = [], set()
    for p in range(1, max_pages + 1):
        url = f'{LIR_SEARCH}&page={p}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode('utf-8', 'replace')
        except Exception as e:
            print(f'  [LIR page {p}] erreur: {e}')
            break
        # Split by offer containers
        chunks = re.split(r'<div class="offer-container"', html)[1:]
        page_count = 0
        for chunk in chunks:
            # Job ID
            id_m = re.search(r'data-offer-id="(\d+)"', chunk)
            if not id_m:
                continue
            job_id = id_m.group(1)
            if job_id in seen_ids:
                continue
            # Title
            tm = re.search(r'<h3[^>]*class="offer-card__title"[^>]*>([\s\S]*?)</h3>', chunk)
            if not tm:
                continue
            title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
            # Company
            cm = re.search(r'<span[^>]*class="company[^"]*"[^>]*>([\s\S]*?)</span>', chunk)
            company = re.sub(r'<[^>]+>', '', cm.group(1)).strip() if cm else ''
            if not company:
                continue
            # Location: after company span "- City (PostalCode)"
            loc_m = re.search(r'</span>\s*-\s*([\w\s\-éèêàùîôœç]+?)\s*\((\d{5})\)', chunk)
            city   = loc_m.group(1).strip() if loc_m else ''
            postal = loc_m.group(2) if loc_m else ''
            # Date
            date_m = re.search(r'(il y a [\d]+ \w+|aujourd)', chunk)
            age = lir_parse_age(date_m.group(1)) if date_m else 99
            # Link
            link_m = re.search(r'href="(/candidat/offre/\d+)"', chunk)
            link = LIR_BASE + link_m.group(1) if link_m else '#'
            seen_ids.add(job_id)
            page_count += 1
            jobs.append({
                'id': 600000 + len(jobs),
                'title': title,
                'company': company,
                'link': link,
                'desc': '',
                'location': ms_normalize_location(city, postal),
                'category': ft_category(title, ''),
                'daysAgo': age,
                'isESN': is_esn(company),
                'source': 'lir',
            })
        print(f'  [LIR page {p}] {page_count} offres → {len(jobs)} total')
        if page_count == 0:
            break
    return jobs

# ── APEC ─────────────────────────────────────────────────────────────────────

APEC_BASE   = 'https://www.apec.fr'
APEC_LOGIN  = APEC_BASE + '/.apec-login.do'
APEC_SEARCH = APEC_BASE + '/cms/webservices/rechercheOffre'
APEC_BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

def apec_login():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPCookieProcessor(cj),
    )
    # Seed cookies with homepage visit
    opener.open(urllib.request.Request(APEC_BASE + '/', headers=APEC_BASE_HEADERS), timeout=10)
    # POST login
    payload = urllib.parse.urlencode({
        'source': 'loginApec',
        'username': APEC_EMAIL,
        'password': APEC_PASSWORD,
    }).encode()
    h = dict(APEC_BASE_HEADERS)
    h.update({
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'cache-control': 'no-cache',
        'Origin': APEC_BASE,
        'Referer': APEC_BASE + '/',
    })
    opener.open(urllib.request.Request(APEC_LOGIN, data=payload, headers=h), timeout=15)
    return opener

def _apec_decode(resp):
    raw = resp.read()
    enc = resp.headers.get('Content-Encoding', '')
    if enc == 'gzip':
        raw = gzip.decompress(raw)
    elif enc == 'br':
        try:
            import brotli
            raw = brotli.decompress(raw)
        except Exception:
            pass
    try:
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return json.loads(raw.decode('latin-1'))

def fetch_apec(max_results=200):
    if not APEC_EMAIL or not APEC_PASSWORD:
        print('  Credentials APEC absents, ignoré')
        return []
    try:
        opener = apec_login()
    except Exception as e:
        print(f'  APEC login erreur: {e}')
        return []

    h2 = dict(APEC_BASE_HEADERS)
    h2.update({
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'Referer': APEC_BASE + '/candidat/recherche-emploi.html/emploi',
        'Origin': APEC_BASE,
    })

    jobs, start, batch = [], 0, 50
    while len(jobs) < max_results:
        body = json.dumps({
            'typesConvention': [143684],   # CDI
            'fonctions': [101833],          # Informatique
            'secteursActivite': [],
            'motsCles': '',
            'lieux': [],
            'pagination': {'startIndex': start, 'range': batch},
        }).encode('utf-8')
        req = urllib.request.Request(APEC_SEARCH, data=body, headers=h2, method='POST')
        try:
            resp = opener.open(req, timeout=20)
            data = _apec_decode(resp)
        except Exception as e:
            print(f'  APEC search erreur (start={start}): {e}')
            break

        results = data.get('resultats', [])
        if not results:
            break

        for r in results:
            # Company from logo URL
            company = ''
            logo = r.get('urlLogo', '')
            if logo:
                m = re.search(r'/logo_(.+?)_\d+_\d+\.', logo)
                if m:
                    company = m.group(1).replace('_', ' ').replace('-', ' ').title()
            if not company:
                continue  # skip anonymous offers

            # Location
            lieu = r.get('lieuTexte', '')
            lm = re.match(r'(.+?)\s*-\s*(\d+)', lieu)
            if lm:
                location = ms_normalize_location(lm.group(1).strip(), lm.group(2))
            else:
                location = lieu.strip() or 'France'

            # Age
            date_str = r.get('datePublication', '')
            try:
                dp = datetime.fromisoformat(date_str.replace('.000+0000', '+00:00'))
                age = max(0, (datetime.now(timezone.utc) - dp).days)
            except Exception:
                age = 99

            title = r.get('intitule', '')
            jobs.append({
                'id': 700000 + len(jobs),
                'title': title,
                'company': company,
                'link': f'{APEC_BASE}/candidat/recherche-emploi.html/offre/{r.get("numeroOffre", "")}',
                'desc': re.sub(r'<[^>]+>', ' ', r.get('texteOffre', '')).strip()[:200],
                'location': location,
                'category': ft_category(title, ''),
                'daysAgo': age,
                'isESN': is_esn(company),
                'source': 'apec',
            })

        print(f'  [APEC] start={start} +{len(results)} → {len(jobs)} total')
        start += batch
        total = data.get('totalCount', 0)
        if start >= total:
            break

    return jobs

# ── FashionJobs ───────────────────────────────────────────────────────────────

FJ_BASE   = 'https://fr.fashionjobs.com'
FJ_SEARCH = (FJ_BASE + '/s/?categories%5B%5D=17'
             '&metier%5B17%5D%5B%5D=248&metier%5B17%5D%5B%5D=263'
             '&metier%5B17%5D%5B%5D=164&metier%5B17%5D%5B%5D=118'
             '&metier%5B17%5D%5B%5D=264&metier%5B17%5D%5B%5D=247'
             '&metier%5B17%5D%5B%5D=177&metier%5B17%5D%5B%5D=119'
             '&contrats%5B%5D=1')
FJ_EXTRA  = ('&categories%5B%5D=17'
             '&metier%5B17%5D%5B%5D=248&metier%5B17%5D%5B%5D=263'
             '&metier%5B17%5D%5B%5D=164&metier%5B17%5D%5B%5D=118'
             '&metier%5B17%5D%5B%5D=264&metier%5B17%5D%5B%5D=247'
             '&metier%5B17%5D%5B%5D=177&metier%5B17%5D%5B%5D=119'
             '&contrats%5B%5D=1')

def fetch_fashionjobs(max_pages=3):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('  Playwright non disponible, FashionJobs ignoré')
        return []

    jobs, seen_ids = [], set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        bpage = browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            locale='fr-FR',
        )

        for page_num in range(1, max_pages + 1):
            url = FJ_SEARCH if page_num == 1 else f'{FJ_BASE}/s/?page={page_num}{FJ_EXTRA}'
            try:
                bpage.goto(url, wait_until='networkidle', timeout=30000)
            except Exception as e:
                print(f'  [FJ p{page_num}] erreur: {e}')
                break

            results = bpage.evaluate('''() => {
                return Array.from(document.querySelectorAll('.js-job-item')).map(card => {
                    const titleEl = card.querySelector('h3 span.tw-line-clamp-2');
                    const title   = titleEl ? titleEl.textContent.trim() : '';

                    const coEl   = card.querySelector('.tw-text-grey-default.tw-uppercase span');
                    const company = coEl ? coEl.textContent.trim() : '';

                    const linkEl = card.querySelector('[data-lien*="fashionjobs.com/redir/"]');
                    const link   = linkEl ? linkEl.getAttribute('data-lien')
                                 : (card.querySelector('a[href*="/emploi/"]')?.href || '#');

                    const locIcon = card.querySelector('[data-icon="location_on"]');
                    const location = locIcon && locIcon.nextElementSibling
                                     ? locIcon.nextElementSibling.textContent.trim() : '';

                    const dateEl  = card.querySelector('span.time-ago[data-value]');
                    const dateVal = dateEl ? dateEl.getAttribute('data-value') : '';

                    return { title, company, link, location, dateVal };
                });
            }''')

            page_count = 0
            for r in results:
                if not r['title']:
                    continue
                # skip anonymous
                co = r['company']
                if not co or co.upper() == 'CONFIDENTIEL':
                    continue
                # deduplicate by link
                link = r['link']
                job_id = re.search(r'(\d{6,})', link)
                job_id = job_id.group(1) if job_id else link
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # date
                try:
                    from datetime import datetime, timezone
                    dp = datetime.fromisoformat(r['dateVal'])
                    if dp.tzinfo is None:
                        dp = dp.replace(tzinfo=timezone.utc)
                    age = max(0, (datetime.now(timezone.utc) - dp).days)
                except Exception:
                    age = 99

                location = ms_normalize_location(r['location'], '') if r['location'] else 'France'
                page_count += 1
                jobs.append({
                    'id': 800000 + len(jobs),
                    'title': r['title'],
                    'company': co,
                    'link': link,
                    'desc': '',
                    'location': location,
                    'category': ft_category(r['title'], ''),
                    'daysAgo': age,
                    'isESN': is_esn(co),
                    'source': 'fj',
                })

            print(f'  [FJ p{page_num}] {page_count} offres → {len(jobs)} total')
            if page_count == 0:
                break

        browser.close()

    return jobs

# ── Indeed ───────────────────────────────────────────────────────────────────

INDEED_BASE = 'https://fr.indeed.com'
INDEED_KEYWORDS = [
    # Backend – language-specific to avoid overlap
    'développeur Python',
    'développeur Java',
    'développeur PHP Symfony',
    'développeur C# .NET',
    'développeur C++',
    # Frontend / Mobile
    'développeur React',
    'développeur Angular Vue',
    'développeur iOS Android',
    # Fullstack
    'développeur fullstack',
    # Data / AI
    'data engineer',
    'data scientist',
    'data analyst',
    'machine learning MLOps',
    # Infra / Cloud / Sec
    'ingénieur DevOps Kubernetes',
    'architecte cloud AWS Azure',
    'analyste cybersécurité',
    # Product / Design
    'product owner scrum',
    'UX designer',
]

def indeed_parse_age(text):
    t = (text or '').lower()
    if any(x in t for x in ['nouveau', 'aujourd', 'heure', 'minute', 'today']): return 0
    m = re.search(r'il y a (\d+)\s*(jour|semaine|mois)', t)
    if not m: return 0  # default recent (sorted by date)
    n = int(m.group(1))
    if 'semaine' in m.group(2): return n * 7
    if 'mois' in m.group(2): return n * 30
    return n

def fetch_indeed():
    """One fresh browser context per keyword bypasses Indeed's per-session block.
    Each keyword yields ~16 unique results; 18 keywords → 150+ total.
    """
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
    except ImportError:
        print('  Playwright / playwright-stealth non disponible, Indeed ignoré')
        return []

    EXTRACT_JS = '''() => {
        return Array.from(document.querySelectorAll('[data-testid="slider_item"]')).map(card => {
            const jkEl = card.querySelector("[data-jk]");
            const jk   = jkEl ? jkEl.getAttribute("data-jk") : "";
            const h2   = card.querySelector("h2.jobTitle, h2");
            const title = h2 ? h2.textContent.trim() : "";
            const co   = card.querySelector('[data-testid="company-name"]');
            const company = co ? co.textContent.trim() : "";
            const loc  = card.querySelector('[data-testid="text-location"]');
            const location = loc ? loc.textContent.trim() : "";
            const allText  = card.innerText || "";
            const dateMatch = allText.match(/il y a \\d+\\s*(jour|heure|minute|semaine|mois)/i)
                           || allText.match(/(nouveau|aujourd)/i);
            const dateText = dateMatch ? dateMatch[0] : "";
            return { jk, title, company, location, dateText };
        });
    }'''

    stealth = Stealth(navigator_platform_override='MacIntel')
    jobs, seen_ids = [], set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        for kw in INDEED_KEYWORDS:
            # Fresh context per keyword — resets session/cookie state that triggers security check
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                locale='fr-FR',
                viewport={'width': 1280, 'height': 900},
                timezone_id='Europe/Paris',
            )
            page = context.new_page()
            stealth.apply_stealth_sync(page)

            enc = urllib.parse.quote(kw)
            # Use &sc= for native CDI filter (avoids keyword contamination with "+CDI")
            url = f'{INDEED_BASE}/jobs?q={enc}&l=France&sc=0kf%3Ajt%28permanent%29%3B&sort=date&start=0'
            kw_count = 0
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2500)
                title = page.title()
                if 'Security Check' in title or 'Connexion' in title:
                    print(f'  [Indeed] "{kw}" → bloqué ({title[:30]})')
                    context.close()
                    continue

                results = page.evaluate(EXTRACT_JS)
                for r in results:
                    jk = r['jk']
                    if not jk or not r['title'] or not r['company']:
                        continue
                    if jk in seen_ids:
                        continue
                    seen_ids.add(jk)

                    raw_loc = r['location']
                    city_m = re.search(r'(?:à\s+)?([A-ZÀ-Ÿa-zà-ÿ\s\-]+?)\s*(?:\((\d{2})\d*\)|(\d{5}))?$', raw_loc)
                    if city_m:
                        city = city_m.group(1).strip()
                        dept = city_m.group(2) or (city_m.group(3)[:2] if city_m.group(3) else '')
                        location = ms_normalize_location(city, dept)
                    else:
                        location = 'France'
                    if 'télétravail' in raw_loc.lower() or 'remote' in raw_loc.lower():
                        location = 'Remote'

                    kw_count += 1
                    jobs.append({
                        'id': 900000 + len(jobs),
                        'title': r['title'],
                        'company': r['company'],
                        'link': f'{INDEED_BASE}/viewjob?jk={jk}',
                        'desc': '',
                        'location': location,
                        'category': ft_category(r['title'], ''),
                        'daysAgo': indeed_parse_age(r['dateText']),
                        'isESN': is_esn(r['company']),
                        'source': 'indeed',
                    })
            except Exception as e:
                print(f'  [Indeed] "{kw}" erreur: {e}')
            finally:
                context.close()

            print(f'  [Indeed] "{kw}" +{kw_count} → {len(jobs)} total')

        browser.close()

    return jobs

# ── Logos (Clearbit Autocomplete) ────────────────────────────────────────────

CLEARBIT_AC = 'https://autocomplete.clearbit.com/v1/companies/suggest?query='

def _name_match(query, result_name):
    """Return True if result_name is plausibly the same company as query.
    Uses bidirectional token overlap: shared tokens must represent ≥50% of
    BOTH the query and the result (prevents "Orange" → "Orange County Register").
    """
    STOP = {'sa', 'sas', 'srl', 'inc', 'ltd', 'group', 'groupe', 'france',
            'the', 'de', 'du', 'le', 'la', 'les', 'et', 'and', 'co', 'corp'}
    def tokens(s):
        return set(re.sub(r'[^a-z0-9\s]', '', s.lower()).split()) - STOP
    qt = tokens(query)
    rt = tokens(result_name)
    if not qt or not rt:
        return False
    shared = qt & rt
    # Bidirectional: majority of BOTH sets must overlap
    return (len(shared) / len(qt) >= 0.5) and (len(shared) / len(rt) >= 0.5)

def _fetch_logo(company):
    """Return (company_lower, logo_url) or (company_lower, '') on miss/error.
    Strategy: Clearbit Autocomplete → name-similarity check → Google Favicon sz=128.
    Only returns a URL when Clearbit's result plausibly matches the company name.
    """
    key = company.lower().strip()
    if not key:
        return key, ''
    try:
        url = CLEARBIT_AC + urllib.parse.quote(company)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = json.loads(urllib.request.urlopen(req, context=ctx, timeout=8).read())
        if data and data[0].get('domain'):
            result_name = data[0].get('name', '')
            domain = data[0]['domain']
            if _name_match(company, result_name):
                return key, f'https://www.google.com/s2/favicons?domain={domain}&sz=128'
    except Exception:
        pass
    return key, ''

def enrich_logos(jobs):
    """Fetch Clearbit logos for all unique company names in parallel, add 'logo' field."""
    unique = list({j['company'] for j in jobs if j.get('company')})
    logo_map = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for key, url in ex.map(_fetch_logo, unique):
            logo_map[key] = url
    found = sum(1 for v in logo_map.values() if v)
    print(f'  Logos: {found}/{len(unique)} entreprises trouvées')
    for j in jobs:
        j['logo'] = logo_map.get((j.get('company') or '').lower().strip(), '')
    return jobs

# ── RecruitCRM enrichment ─────────────────────────────────────────────────────

RCRM_BASE = 'https://api.recruitcrm.io/v1'
RCRM_APP  = 'https://app.recruitcrm.io'

def _rcrm_get(path, params=None):
    """Authenticated GET against RecruitCRM API. Returns parsed JSON or None."""
    url = RCRM_BASE + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {RECRUITCRM_TOKEN}',
        'Accept': 'application/json',
        'User-Agent': 'JobRadar/1.0',
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        return json.loads(resp.read())
    except Exception:
        return None

CRM_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crm_cache.json')

def _load_crm_lookup():
    """Load CRM company lookup from local cache file (built weekly by build_crm_cache.py).
    Falls back to live API (first 25 pages) if cache is missing.
    Returns (companies dict, users dict).
    """
    if os.path.exists(CRM_CACHE_FILE):
        try:
            with open(CRM_CACHE_FILE, encoding='utf-8') as f:
                cache = json.load(f)
            companies = cache.get('companies', {})
            users = {str(k): v for k, v in cache.get('users', {}).items()}
            print(f'  [CRM] Cache local : {len(companies)} entreprises, {len(users)} consultants (mis à jour {cache.get("updated","?")[:10]})')
            return companies, users
        except Exception as e:
            print(f'  [CRM] Cache illisible ({e}), fallback API...')

    if not RECRUITCRM_TOKEN:
        return {}, {}

    # Fallback: live API, first 25 pages
    print('  [CRM] Pas de cache — chargement API (25 pages max)...')
    lookup = {}
    for page in range(1, 26):
        data = _rcrm_get('/companies', {'per_page': 100, 'page': page})
        if not data:
            break
        items = data.get('data', [])
        if not items:
            break
        for c in items:
            name = (c.get('company_name') or '').strip()
            if not name:
                continue
            slug = c.get('slug') or str(c.get('id') or '')
            crm_link = f'https://app.recruitcrm.io/v1/company/{slug}' if slug else ''
            status = ''
            for cf in c.get('custom_fields', []):
                if cf.get('field_name') == 'Company Status':
                    status = (cf.get('value') or '').strip()
                    break
            lookup[name.lower()] = {
                'crm_link': crm_link, 'is_client': status == 'Active Account',
                'status': status, 'company_name': name,
                'numeric_id': c.get('id'), 'owner_id': c.get('owner'),
            }
        print(f'    [CRM] page {page} → {len(items)} (total {len(lookup)})')
        if len(items) < 100:
            break
    return lookup, {}

def _fetch_company_jobs(numeric_id):
    """Fetch jobs for one company. Returns (has_tc, has_open_job, open_job_owner_id).
    has_tc = any job exists (open or closed) → T&Cs signed.
    """
    import time as _time
    data = _rcrm_get('/jobs', {'company_id': numeric_id, 'per_page': 50})
    if not data:
        return None, None, None
    jobs_list = data.get('data', [])
    has_tc = len(jobs_list) > 0
    open_jobs = [j for j in jobs_list if (j.get('job_status') or {}).get('label') == 'Open']
    has_open = len(open_jobs) > 0
    owner_id = open_jobs[0].get('owner') if open_jobs else None
    return has_tc, has_open, owner_id

def enrich_crm(jobs):
    """Add CRM fields to each job: crm_link, is_client, crm_status,
    crm_tc (T&Cs signed), crm_open_job, crm_consultant (paternité)."""
    import time as _time

    if not RECRUITCRM_TOKEN and not os.path.exists(CRM_CACHE_FILE):
        print('  Token RECRUITCRM absent et pas de cache, enrichissement CRM ignoré')
        for j in jobs:
            j.update({'crm_link':'','is_client':False,'crm_status':'','crm_tc':None,'crm_open_job':False,'crm_consultant':''})
        return jobs

    crm_lookup, users = _load_crm_lookup()
    if not crm_lookup:
        for j in jobs:
            j.update({'crm_link':'','is_client':False,'crm_status':'','crm_tc':None,'crm_open_job':False,'crm_consultant':''})
        return jobs

    # Build match map on unique company names only
    unique_companies = list({(j.get('company') or '').strip() for j in jobs if j.get('company')})
    match_map = {}
    for company in unique_companies:
        key = company.lower()
        if key in crm_lookup:
            match_map[company] = crm_lookup[key]
        else:
            match_map[company] = next(
                (v for v in crm_lookup.values() if _name_match(company, v['company_name'])),
                None
            )

    # Enrich matched clients + prospects with job details (T&Cs / job ouvert / consultant)
    if RECRUITCRM_TOKEN:
        to_enrich = {
            co: rec for co, rec in match_map.items()
            if rec and rec.get('numeric_id') and (rec.get('is_client') or rec.get('status') == 'Prospect')
        }
        if to_enrich:
            print(f'  [CRM] Enrichissement jobs pour {len(to_enrich)} entreprises (clients + prospects)...')
            _t0 = _time.time()
            for i, (company, rec) in enumerate(to_enrich.items()):
                has_tc, has_open, job_owner_id = _fetch_company_jobs(rec['numeric_id'])
                rec['crm_tc']        = has_tc
                rec['crm_open_job']  = has_open if has_open is not None else False
                # Paternité: open job owner > company owner
                consultant_id = job_owner_id or rec.get('owner_id')
                rec['crm_consultant'] = users.get(str(consultant_id), '') if consultant_id else ''
                # Rate limit: 60 req/min → 1 req/s
                elapsed = _time.time() - _t0 - i
                if elapsed < 1.0:
                    _time.sleep(1.0 - elapsed)
            print(f'  [CRM] Enrichissement terminé en {int(_time.time()-_t0)}s')

    matched = clients = prospects = 0
    for j in jobs:
        company = (j.get('company') or '').strip()
        res = match_map.get(company)
        if res:
            j['crm_link']       = res['crm_link']
            j['is_client']      = res['is_client']
            j['crm_status']     = res.get('status', '')
            j['crm_tc']         = res.get('crm_tc', None)      # True/False/None
            j['crm_open_job']   = res.get('crm_open_job', False)
            j['crm_consultant'] = res.get('crm_consultant', '')
            matched += 1
            if res['is_client']:      clients += 1
            elif res.get('status') == 'Prospect': prospects += 1
        else:
            j.update({'crm_link':'','is_client':False,'crm_status':'','crm_tc':None,'crm_open_job':False,'crm_consultant':''})

    print(f'  CRM: {matched}/{len(jobs)} offres matchées — {clients} clients actifs, {prospects} prospects')
    return jobs

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

    print('Fetch HelloWork...')
    try:
        hw = fetch_hellowork(pages_per_kw=2)
        jobs += hw
        print(f'  {len(hw)} CDI HelloWork')
    except Exception as e:
        print(f'  HelloWork erreur: {e}')

    print("Fetch L'Industrie Recrute...")
    try:
        lir = fetch_lir(max_pages=6)
        jobs += lir
        print(f"  {len(lir)} CDI L'Industrie Recrute")
    except Exception as e:
        print(f"  L'Industrie Recrute erreur: {e}")

    print('Fetch APEC...')
    try:
        apec = fetch_apec(max_results=200)
        jobs += apec
        print(f'  {len(apec)} CDI APEC')
    except Exception as e:
        print(f'  APEC erreur: {e}')

    print('Fetch FashionJobs...')
    try:
        fj = fetch_fashionjobs(max_pages=3)
        jobs += fj
        print(f'  {len(fj)} CDI FashionJobs')
    except Exception as e:
        print(f'  FashionJobs erreur: {e}')

    print('Fetch Indeed...')
    try:
        ind = fetch_indeed()
        jobs += ind
        print(f'  {len(ind)} CDI Indeed')
    except Exception as e:
        print(f'  Indeed erreur: {e}')

    print(f'Total: {len(jobs)} offres')
    print('Enrichissement logos...')
    try:
        enrich_logos(jobs)
    except Exception as e:
        print(f'  Logos erreur: {e}')
        for j in jobs:
            j.setdefault('logo', '')

    print('Enrichissement CRM...')
    try:
        enrich_crm(jobs)
    except Exception as e:
        print(f'  CRM erreur: {e}')
        for j in jobs:
            j.setdefault('crm_link', '')
            j.setdefault('is_client', False)

    updated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    template = open('template.html', encoding='utf-8').read()
    html = (template
            .replace('__JOBS__', json.dumps(jobs, ensure_ascii=False))
            .replace('"__UPDATED__"', f'"{updated}"'))

    os.makedirs('docs', exist_ok=True)
    open('docs/index.html', 'w', encoding='utf-8').write(html)
    print('docs/index.html généré')
