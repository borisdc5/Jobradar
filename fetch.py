import urllib.request, ssl, json, re, os
from datetime import datetime, timezone

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

AFJV_RSS = 'https://emploi.afjv.com/rss.xml'
FT_RSS   = 'https://recrute.francetravail.org/handlers/offerRss.ashx?LCID=1036&Rss_Contract=577'

ESN = ['capgemini','atos','sopra','accenture','michael page','hays','robert half','manpower','adecco','randstad','sqli','altran','alten','aubay','devoteam','wavestone','kpmg','deloitte','pwc','umaneer','experis','modis']

def is_esn(company):
    c = (company or '').lower()
    return any(e in c for e in ESN)

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, context=ctx, timeout=15).read().decode('utf-8')

def days_ago(pub):
    try:
        from email.utils import parsedate_to_datetime
        return max(0, (datetime.now(timezone.utc) - parsedate_to_datetime(pub)).days)
    except:
        return 99

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
        def g(tag):
            m = re.search(r'<'+tag+r'[^>]*>(.*?)</'+tag+r'>', item, re.DOTALL)
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

# ── France Travail ─────────────────────────────────────────────────────────────

CITY_MAP = {
    'paris':'Paris','ile-de-france':'Paris','hauts-de-seine':'Paris','seine-saint-denis':'Paris',
    'val-de-marne':'Paris','val-d\'oise':'Paris','seine-et-marne':'Paris','yvelines':'Paris',
    'essonne':'Paris','creteil':'Paris','nanterre':'Paris','montrouge':'Paris',
    'lyon':'Lyon','villeurbanne':'Lyon','grenoble':'Grenoble',
    'bordeaux':'Bordeaux','gironde':'Bordeaux',
    'rennes':'Rennes','bretagne':'Rennes',
    'nantes':'Nantes','loire-atlantique':'Nantes',
    'montpellier':'Montpellier','balma':'Toulouse',
    'toulouse':'Toulouse','haute-garonne':'Toulouse',
    'lille':'Lille','nord':'Lille','valenciennes':'Lille',
    'marseille':'Marseille','aix':'Marseille','bouches-du-rhône':'Marseille',
    'strasbourg':'Strasbourg','bas-rhin':'Strasbourg',
    'nice':'Nice','alpes-maritimes':'Nice',
    'remote':'Remote','teletravail':'Remote','télétravail':'Remote',
}

def ft_location(raw):
    raw_low = raw.strip().lower()
    for k, v in CITY_MAP.items():
        if k in raw_low: return v
    return raw.strip().title() if raw.strip() else 'France'

def ft_parse_title(raw):
    # Remove reference prefix "2026-XXXXX - "
    s = re.sub(r'^\d{4}-\d+ - ', '', raw).strip()
    parts = s.rsplit(' - ', 1)
    if len(parts) == 2:
        return parts[0].strip().title(), ft_location(parts[1])
    return s.title(), 'France'

def parse_ft(xml):
    jobs = []
    for i, item in enumerate(re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)):
        def g(tag):
            m = re.search(r'<'+tag+r'[^>]*>(.*?)</'+tag+r'>', item, re.DOTALL)
            return m.group(1).strip() if m else ''
        desc = re.sub(r'<[^>]+>', ' ', g('description')).strip()
        title, location = ft_parse_title(g('title'))
        jobs.append({'id': 100000 + i, 'title': title, 'company': 'France Travail',
                     'link': g('link'), 'desc': desc[:200], 'location': location,
                     'category': '', 'daysAgo': days_ago(g('pubDate')),
                     'isESN': False, 'source': 'ft'})
    return jobs

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    jobs = []

    print('Fetch AFJV...')
    try:
        jobs += parse_afjv(fetch(AFJV_RSS))
        print(f'  {sum(1 for j in jobs if j["source"]=="afjv")} CDI AFJV')
    except Exception as e:
        print(f'  AFJV erreur: {e}')

    print('Fetch France Travail...')
    try:
        ft_jobs = parse_ft(fetch(FT_RSS))
        jobs += ft_jobs
        print(f'  {len(ft_jobs)} CDI France Travail')
    except Exception as e:
        print(f'  France Travail erreur: {e}')

    print(f'Total: {len(jobs)} CDI')
    updated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    template = open('template.html', encoding='utf-8').read()
    html = template.replace('__JOBS__', json.dumps(jobs, ensure_ascii=False)).replace('"__UPDATED__"', f'"{updated}"')

    os.makedirs('docs', exist_ok=True)
    open('docs/index.html', 'w', encoding='utf-8').write(html)
    print('docs/index.html généré')
