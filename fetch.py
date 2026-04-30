import urllib.request, ssl, json, re, os
from datetime import datetime, timezone

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ESN = ['capgemini','atos','sopra','accenture','michael page','hays','robert half','manpower','adecco','randstad','sqli','altran','alten','aubay','devoteam','wavestone','kpmg','deloitte','pwc','umaneer','experis','modis']

def is_esn(company):
    c = (company or '').lower()
    return any(e in c for e in ESN)

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, context=ctx, timeout=15).read().decode('utf-8')

def extract_company(desc):
    m = re.match(r'^(.+?)\s+recrute', desc, re.IGNORECASE)
    return m.group(1).strip() if m else 'Studio'

def extract_location(desc):
    m = re.search(r'bas[eé]\s+[aà]\s+([^(]+)\s*\((\d{2,3})\)', desc, re.IGNORECASE)
    if not m: return 'France'
    city = m.group(1).strip().lower()
    dept = m.group(2)
    if dept == '00' or any(x in city for x in ['teletravail','télétravail','remote']): return 'Remote'
    if dept in ['75','92','93','94','95','77','78','91'] or any(x in city for x in ['paris','boulogne','nanterre','montrouge','issy','cergy','romainville','bagnolet','lognes']): return 'Paris'
    if dept == '69' or any(x in city for x in ['lyon','villeurbanne']): return 'Lyon'
    if dept == '33' or 'bordeaux' in city: return 'Bordeaux'
    if dept == '35' or 'rennes' in city: return 'Rennes'
    if dept == '44' or 'nantes' in city: return 'Nantes'
    if dept == '34' or 'montpellier' in city: return 'Montpellier'
    if dept == '31' or 'toulouse' in city: return 'Toulouse'
    if dept == '59' or any(x in city for x in ['lille','valenciennes']): return 'Lille'
    if dept == '13' or any(x in city for x in ['marseille','aix']): return 'Marseille'
    return m.group(1).strip()

def days_ago(pub):
    try:
        from email.utils import parsedate_to_datetime
        d = parsedate_to_datetime(pub)
        now = datetime.now(timezone.utc)
        return max(0, (now - d).days)
    except:
        return 99

def parse_rss(xml):
    jobs = []
    items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
    for i, item in enumerate(items):
        def g(tag):
            m = re.search(r'<'+tag+r'[^>]*>(.*?)</'+tag+r'>', item, re.DOTALL)
            return m.group(1).strip() if m else ''
        title = g('title')
        desc = re.sub(r'<[^>]+>', ' ', g('description')).strip()
        link = g('link')
        pub = g('pubDate')
        cats = re.findall(r'<category>(.*?)</category>', item)
        contrat = ''
        category = ''
        for cat in cats:
            if cat in ['CDI','CDD','Stage','Alternance','Freelance','Intermittent']:
                contrat = cat
            elif cat not in ['France','International','Belgique']:
                category = cat
        if contrat != 'CDI':
            continue
        company = extract_company(desc)
        jobs.append({
            'id': i,
            'title': title,
            'company': company,
            'link': link,
            'desc': desc[:200],
            'location': extract_location(desc),
            'category': category,
            'daysAgo': days_ago(pub),
            'isESN': is_esn(company)
        })
    return jobs

if __name__ == '__main__':
    print('Fetch AFJV RSS...')
    xml = fetch('https://emploi.afjv.com/rss.xml')
    jobs = parse_rss(xml)
    print(f'{len(jobs)} CDI trouvés')

    updated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    template = open('template.html', encoding='utf-8').read()
    html = template.replace('__JOBS__', json.dumps(jobs, ensure_ascii=False)).replace('"__UPDATED__"', f'"{updated}"')

    os.makedirs('docs', exist_ok=True)
    open('docs/index.html', 'w', encoding='utf-8').write(html)
    print('docs/index.html généré')
