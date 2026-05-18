import urllib.request, urllib.parse, ssl, json, re, os, gzip, http.cookiejar, time
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

CABINETS = [
    # Intérim / staffing majeurs
    'adecco','manpower','randstad','expectra','synergie','start people','supplay',
    'proman','partnaire','menway','ergalis','adéquat','adequat','abalone',
    'domino rh','domino care','domino staff','domino missions',
    'aquila rh','lynx rh','vitalis médical','vitalis medical',
    'temporis','samsic','triangle solutions','triangle intérim','triangle interim',
    'jubil','dlsi','connectt','sup interim','ras intérim','ras interim','ras recrutement',
    'ras transport','option intérim','option interim','leader intérim','leader interim',
    'actual leader','kelly services','kelly scientifique','kelly finance',
    # Cabinets de recrutement / search firms
    'page personnel','michael page','robert half','hays','walters people','robert walters',
    'fed group','fed business','fed finance','fed it','fed supply','fed construction',
    'fed engineering','fed human','fed legal','fed santé','fyte',
    'spring professional','spring france','lhh','appel médical','appel medical',
    'jbm médical','jbm medical','winsearch','selescope','vidal associates',
    'morgan philips','hudson france','perfhomme','lincoln group','lincoln recrutement',
    'alphéa','alphea','harry hope','adsearch','phi rh','solve recrutement',
    'ignition program','mozaik rh','talent.io','hiresweet','recrulab',
    'nonstop consulting','nigel frank','progressive recruitment','washington frank',
    'computer futures','euro london','alexander b. smith','badenoch',
    'rh partners','solinki','orientaction','talentpeople','ccld',
    'seyos','mobiskill','easy partner','skillink','externatic',
    'avizio','arravati','blue coders','the product crew',
    # Recrutement digital / tech / niches
    'lynkus','uptoo','altaide','urban linker','silkhom','data recrutement',
    'licorne society','getpro','kicklox','blue search conseil',
    'elaee','finaïa','finaia','talent program','jobberry','profil partenaire',
    'opensourcing','circular search','hartstone','human solutions',
    'dream catcher','effektiv','macandr','fusion rh','co-efficience',
    'ethika','elatos','batenborch','work&you','nextgen rh',
    'florian mantione','ethis rh','solutio rh','cooptalis','keyman',
    'mind partners','sapiance','vauban executive','turningpoint','persuaders',
    'potentiel conseil','lobster hfs','impactup','in quarto','light consultants',
    'cadres en mission','talentup','search & selection','rc human',
    'aptic conseil','avantage consulting','bmc consultants','phoenix consulting',
    'centurion search','publika','mcg engineering','otteo rh','viamedis rh',
    'rexel rh','kaducé','kaduce','h&r recrutement','alphyr',
    'talent expert','remotive','hunteed','mozaik',
    'clémentine','clementine','amalo','cofabrik','bluedocker',
    "cadr'avenir",'cadravenir','perfia','winid','aéos','aeos',
    'charly recrutement','job link','morgan services',
    'interaction santé','interaction btp','interaction naval',
    'proman santé','proman btp','proman expertise',
    'adéquat inside','adéquat recrutement',
    'groupe actual','groupe crit','groupe menway','groupe synergie','groupe partnaire',
    'groupe domino','groupe interaction','groupe morgan','groupe proman','groupe dlsi',
    'groupe ras','groupe jubil','groupe abalone','groupe triangle','groupe connectt',
    'groupe samsic','groupe leader','groupe ergalis',
    # Ajouts
    'cimem','jober group','skills cadres','fab group','karpos','timtargett',
    'kara travail','team.is','crit interim','kent recrutement','experteam',
    'w hunt','horizon job','cabinet gascon','abil ressources',
    'les interimaires','advance emploi','talents handicap',
    'asap work','innova solutions',
    'taste','awake group','skiils','pastèque','pasteque','matchee','caboost',
    'sherpa accompagnement','ergon recruitment','bloomays','arbalett',
    'surfjob','easy-talent','easy talent','rheso','le bureau des talents','bureau des talents',
    'darwin partners','mercato de l\'emploi','danem people france','recrut\'',
    'easypartner','sotalent','so talent','jobgether',
]

ESNS = [
    # ESN Tier 1
    'capgemini','atos','sopra','accenture','alten','aubay','devoteam','wavestone',
    'sqli','altran','umaneer','experis','modis','itekway','alteca','informatis',
    'groupe open',
    # ESN mid-market
    'blue soft','kaliop','conserto','xebia','exalt','eleven labs','niji',
    'makina corpus','sensiolabs','clever age','synolia','izberg','yield studio',
    'theodo','fabernovel','betomorrow','jems','advens','i-tracing',
    'almond','nomios','apixit','synetis','intrinsec','wifirst','systonic',
    'cheops technology','adista','celad','agylis','guarani','hn services',
    'objectware','helpline','absys cyborg','dcs easyware','proxiad',
    'addixgroup','koesio','sra informatique','oci informatique','adomik',
    'arondor','meritis','zen value','easis','viveris','isatech','jiliti',
    'ouidou','klanik','skaizen','digital virgo','jouve','coexya',
    'decivision','arolla','carbon it','zenior','aneo','ekimetrics','ysance',
    'avanade','ardemis','acensi','cat-amania','consort group','tmc france',
    'it link','adentis','auberon consulting','geser best','guérin technologies',
    'guerin technologies','oxiane','obeo','inetdoc','vif software','trsb',
    'omnilog','unlck','ocsi','syage','humancraft','adelyce','bial-x',
    'datavalue consulting','tnp consultants','saegus','stanford technologies',
    'isia','micropole','norsys','oxya','apsolut',
    'teamwork france','delaware france','callimedia','cellenza','sam solutions',
    'zenity','net6tem','webnet','useradgents','pentalog','softeam',
    'astrel','kincy','alyotech','rtone','wemanity','noveo','koders',
    'feel europe','acpqualife','afg engineering','afd tech','ametra','aquantic',
    'arhs developments','artelys','askell','atawa','axopen','beelix',
    'brainsonic','c2s bouygues','citech','clostera','codeworks',
    'crayon france','data one','davidson','degetel',
    'digitalberry','divalto','efor group','ekimia','elsys design',
    'emakina','enovea','espritek','etix everywhere','everience',
    'feelagile','finegan','foliateam','galiad','harington','hitechpros',
    'hub one','iobeya','its group','izi solutions','kereon',
    'konsultoo','la javaness','lùkla','lukla','mallyance',
    'maltem','mca engineering','methys','mind7','néosoft','neosoft',
    'noveane','nuxeo','opstim','otimo','performance informatique',
    'pixagility','proelan','proservia','qim info','sogilis','squad',
    'stedia','synchrone','teamnet','tech advantage','tech valley',
    'teksystems','tenth revolution','tersea','the coding machine',
    'timspirit','ucase consulting','upper-link','virtuos','viseatis',
    'waycom','wide agency','xefi','xelya','ygl consulting','zenika',
    'sii atlantique','sii méditerranée','sii méditerranee',
    'sii ouest','sii est','sii services','sii luxembourg',
    # Ajouts
    'arcesi','audensiel','sully group','reisel','nbtech','b-hive',
    'max digital services','avisto','expleo','ikigaï','ikigai','onepoint',
    'spie ics','holenek','sinetik','scalian','hardis group','kanoma',
    'k-lagan','stork groupe','ccl consulting','orange business',
    'size up consulting','ekkiden','inetum','it mates','its services',
    'assystem','infotel','andrice','ingeniance','seequalis',
    'sollers consulting','ciorane','ginko','defi informatique',
    'sea tpi','econocom','akkodis','seres technologies',
    'kaizen solutions','amiltone','groupe sii','inside group','alpee',
    'kp2i','open sourcing','kpmg','yo it consulting','davidson consulting',
    'astek','finance people','artemys','momento','nexton','fortil','talan',
    'celetis','keylink','cegelis',
    'skiils','cenova','algovia','unitech solutions','tlti','raedy','sijo','taleo',
    'inventiv it','alpineo consulting','craftmandata','whub','sapiens group',
    '5 degrés','5 degres','consulting efficiency','obeya it','futurwork',
    'acatus','avnir engineering','sweet it','apya','nexoris','bk consulting',
    'frydom','seven','go&dev','la tribu',
    'skills and affinity','skill now','serv\'it','servit',
]

def is_cabinet(company):
    c = (company or '').lower()
    if any(e in c for e in CABINETS):
        return True
    return 'conseil' in c

def is_esn_company(company):
    c = (company or '').lower()
    if any(e in c for e in ESNS):
        return True
    # "SII" seul (hors sii atlantique etc. déjà couverts)
    if c == 'sii' or c.startswith('sii ') or ' sii ' in c:
        return True
    if ' rh' in c or c.endswith(' rh'):
        return True
    if 'recrutement' in c:
        return True
    return False

def is_esn(company):
    """Compat: renvoie True si cabinet OU ESN (pour backward compat si besoin)."""
    return is_cabinet(company) or is_esn_company(company)

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
        afjv_hint = next((c for c in cats if c not in ['CDI','CDD','Stage','Alternance','Freelance','Intermittent','France','International','Belgique']), '')
        desc = re.sub(r'<[^>]+>', ' ', g('description')).strip()
        company = afjv_company(desc)
        title_afjv = g('title')
        jobs.append({'id': i, 'title': title_afjv, 'company': company, 'link': g('link'),
                     'desc': desc[:200], 'location': afjv_location(desc), 'category': categorize(title_afjv, afjv_hint),
                     'daysAgo': days_ago(g('pubDate')), 'isESN': is_esn_company(company), 'isCabinet': is_cabinet(company), 'source': 'afjv'})
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

_AFJV_MAP = {
    'programmation':            'Développement',
    'data / gestion de données':'Data / IA',
    'devops / cloud':           'DevOps / Cloud',
    'cybersécurité':            'Cybersécurité',
    'product / projet':         'Produit',
    'ux / design':              'Produit',
    'test / qa':                'Produit',
    'management':               'Architecture & Lead',
    'commercial / marketing':   'Marketing',
    'conception':               'Jeux Vidéo',
    'infographie':              'Jeux Vidéo',
    'musique / son':            'Jeux Vidéo',
}

def categorize(title, hint=''):
    # Direct AFJV category mapping
    mapped = _AFJV_MAP.get((hint or '').lower().strip())
    if mapped:
        return mapped
    t = ((title or '') + ' ' + (hint or '')).lower()
    # ── Cybersécurité ──────────────────────────────────────────────────────────
    if any(x in t for x in [
        'cyber','pentest','penetration test','ethical hack','red team','blue team',
        'soc analyst','threat hunt','incident respons','cert analyst','rssi','ciso',
        'security manager','security auditor','iso 27001','iam consultant',
        'iam engineer','pam engineer','devsecops','cloud security',
        'network security','endpoint security','security engineer',
        'offensive security','vulnerability',
    ]): return 'Cybersécurité'
    # ── Data / IA ──────────────────────────────────────────────────────────────
    if any(x in t for x in [
        'data scientist','data engineer','data analyst','data architect','dataops',
        'analytics engineer','etl developer','big data','spark engineer','hadoop',
        'machine learning','deep learning','llm engineer','genai','gen ai',
        'ai engineer','ai architect','ai researcher','ai product','conversational ai',
        'reinforcement learning','computer vision engineer','nlp engineer',
        'prompt engineer','mlops','bi developer','bi consultant','reporting analyst',
        'tableau developer','power bi','qlik developer',
        'dba ','database administrator','postgre','oracle dba','sql server dba',
        'mongodb engineer','mdm consultant','quantitative analyst',
        'applied scientist','research scientist','intelligence artificielle',
        'business intel',
    ]): return 'Data / IA'
    # ── ERP / CRM ──────────────────────────────────────────────────────────────
    if any(x in t for x in [
        'sap consultant','sap developer','sap fi','sap mm','sap sd','sap abap',
        'sap hana','oracle erp','dynamics 365','dynamics crm','sage consultant',
        'infor consultant','salesforce','hubspot consultant','crm manager',
        'power platform','mendix','outsystems','low code','no code',
    ]): return 'ERP / CRM'
    # ── Architecture & Lead ────────────────────────────────────────────────────
    if any(x in t for x in [
        'software architect','solution architect','enterprise architect',
        'technical architect','chief architect',
        'cto','vp engineering','vp tech','vp of eng','engineering manager',
        'head of engineering','tech lead','lead developer','lead engineer',
        'tribe lead','technical director',
    ]): return 'Architecture & Lead'
    # ── DevOps / Cloud ─────────────────────────────────────────────────────────
    if any(x in t for x in [
        'devops','site reliability','sre ','platform engineer','build & release',
        'ci/cd','cloud engineer','cloud architect','aws engineer','azure engineer',
        'gcp engineer','multi-cloud','finops','kubernetes','openshift',
        'container platform','administrateur sys','sysadmin','linux engineer',
        'windows engineer','infrastructure architect','infrastructure manager',
        'unix engineer','administrateur réseau','network engineer','network architect',
        'telecom engineer','voip','sd-wan','noc engineer',
        'ingénieur production','production engineer','ops engineer','run manager',
        'it operations','infrastructure','réseau admin',
    ]): return 'DevOps / Cloud'
    # ── Développement ──────────────────────────────────────────────────────────
    if any(x in t for x in [
        'backend engineer','backend developer','software engineer','software developer',
        'java developer','kotlin developer','scala developer','php developer',
        'python developer','django developer','flask developer','node.js',
        'golang developer','rust developer','.net developer','c# developer',
        'ruby developer','api developer','microservices','application engineer',
        'frontend engineer','javascript developer','typescript developer',
        'react developer','vue.js','angular developer','next.js','nuxt.js',
        'ui developer','mobile web developer',
        'fullstack engineer','full stack engineer','product engineer',
        'ios developer','android developer','flutter developer','react native',
        'swift developer','xamarin','ionic developer','mobile engineer',
        'embedded software','firmware engineer','linux embedded','qt developer',
        'gameplay programmer','game developer','unreal engine','unity developer',
        'graphics programmer','engine programmer',
        'développeur','développeuse','programmeur','ingénieur logiciel',
        'ingénieur développement','ingénieur backend','ingénieur frontend',
        'fullstack','full-stack','frontend','front-end','backend',
        'software eng','logiciel',
    ]): return 'Développement'
    # ── Produit ─────────────────────────────────────────────────────────────────
    if any(x in t for x in [
        'product manager','product owner','head of product','chief product',
        'technical product','ai product manager','growth product',
        'product designer','ux designer','ui designer','ux researcher',
        'service designer','interaction designer','ux writer',
        'product operations','product analyst','product strategist',
        'qa engineer','test engineer','qa analyst','automation tester','sdet',
        'test automation','performance tester','validation engineer',
        'chef de produit',' po ','po,',
    ]): return 'Produit'
    # ── IT Support ──────────────────────────────────────────────────────────────
    if any(x in t for x in [
        'helpdesk','help desk','service desk','desktop support','it support engineer',
        'technicien support','workplace engineer','field support','it technician',
    ]): return 'IT Support'
    # ── Marketing ───────────────────────────────────────────────────────────────
    if any(x in t for x in [
        'growth manager','growth hacker','acquisition manager','performance marketing',
        'sea manager','seo manager','paid media','crm marketing','lifecycle manager',
        'content manager','brand manager','social media manager','community manager',
        'copywriter','editorial manager','influence manager','product marketing',
        'go-to-market',' pmm ','market intelligence','marketing operations',
        'marketing automation','marketing analyst','digital analyst','cro specialist',
        'web analyst','cmo','vp marketing','head of marketing','marketing director',
        'marketing digital','marketing manager',
    ]): return 'Marketing'
    # ── Sales / BizDev ──────────────────────────────────────────────────────────
    if any(x in t for x in [
        'sdr ','bdr ','sales development representative','business development representative',
        'account executive','saas sales','closing manager',
        'key account manager','strategic account manager',
        'presales','pre-sales','solutions consultant','solutions engineer',
        'head of sales','sales director','vp sales','revenue operations',
        'sales operations','partnership manager','channel manager','alliances manager',
        'customer success','customer care manager','onboarding specialist',
        'customer experience manager','implementation consultant',
        'business developer','business development',
        'account manager',
    ]): return 'Sales / BizDev'
    # ── Gestion de Projet ───────────────────────────────────────────────────────
    if any(x in t for x in [
        'chef de projet','technical project manager','digital project manager',
        'infrastructure project manager','erp project manager','delivery lead',
        'program manager','pmo ',
    ]): return 'Gestion de Projet'
    # ── Consulting / Transformation ──────────────────────────────────────────────
    if any(x in t for x in [
        'consultant digital','it consultant','transformation consultant',
        'strategy consultant','innovation consultant','agile coach',
        'change manager','delivery manager','scrum master',
        'project manager','chef de projet it',
    ]): return 'Consulting'
    # ── Broad fallbacks ──────────────────────────────────────────────────────────
    if any(x in t for x in ['directeur technique','dsi','cio','head of tech']):
        return 'Architecture & Lead'
    if any(x in t for x in ['commercial','vente','business dev']):
        return 'Sales / BizDev'
    if any(x in t for x in ['marketing','growth ','seo ','sea ']):
        return 'Marketing'
    if any(x in t for x in ['data ','analyse données']):
        return 'Data / IA'
    return ''

FT_KEYWORDS = [
    # Développement
    'développeur',
    'software engineer',
    # DevOps / Cloud
    'devops',
    'ingénieur cloud',
    'administrateur systèmes',
    # Data / IA
    'data engineer',
    'data scientist',
    'machine learning',
    # Cybersécurité
    'cybersécurité',
    'pentester',
    # Produit / Design
    'product manager',
    'ux designer',
    # ERP / CRM
    'consultant SAP',
    'consultant Salesforce',
    # Archi & Lead
    'architecte logiciel',
    'tech lead',
    # Sales / Marketing
    'business developer',
    'marketing digital',
    # Consulting / Projet
    'consultant transformation',
    'chef de projet informatique',
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
                'category': categorize(title, o.get('romeLibelle', '')),
                'daysAgo': days_ago(o.get('dateCreation', '')),
                'isESN': is_esn_company(company), 'isCabinet': is_cabinet(company),
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
            'isESN': is_esn_company(company), 'isCabinet': is_cabinet(company),
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
            'category': categorize(title, ''),
            'daysAgo': age,
            'isESN': is_esn_company(company), 'isCabinet': is_cabinet(company),
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
                'category': categorize(title, ''),
                'daysAgo': age,
                'isESN': is_esn_company(company), 'isCabinet': is_cabinet(company),
                'source': 'hw',
            }
    except Exception:
        pass
    return None

HW_KEYWORDS = [
    'développeur',
    'ingénieur logiciel',
    'data',
    'devops',
    'cloud',
    'cybersécurité',
    'product manager',
    'ux designer',
    'consultant IT',
    'chef de projet IT',
    'architecte',
    'business developer',
    'marketing digital',
    'salesforce',
    'sap consultant',
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
                'category': categorize(title, ''),
                'daysAgo': age,
                'isESN': is_esn_company(company), 'isCabinet': is_cabinet(company),
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

def fetch_apec(max_results=300):
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
                'category': categorize(title, ''),
                'daysAgo': age,
                'isESN': is_esn_company(company), 'isCabinet': is_cabinet(company),
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
        bpage.set_default_navigation_timeout(30000)
        bpage.set_default_timeout(10000)

        for page_num in range(1, max_pages + 1):
            url = FJ_SEARCH if page_num == 1 else f'{FJ_BASE}/s/?page={page_num}{FJ_EXTRA}'
            try:
                bpage.goto(url, wait_until='domcontentloaded', timeout=30000)
                bpage.wait_for_timeout(2000)
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
                    'category': categorize(r['title'], ''),
                    'daysAgo': age,
                    'isESN': is_esn_company(co), 'isCabinet': is_cabinet(co),
                    'source': 'fj',
                })

            print(f'  [FJ p{page_num}] {page_count} offres → {len(jobs)} total')
            if page_count == 0:
                break

        browser.close()

    return jobs

# ── Indeed ───────────────────────────────────────────────────────────────────

# Indeed removed: blocked 100% from GitHub Actions cloud IPs (Security Check on every request)
# INDEED_BASE = 'https://fr.indeed.com'
INDEED_KEYWORDS = [
    # Backend
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
    # DevOps / Cloud / Infra
    'ingénieur DevOps Kubernetes',
    'architecte cloud AWS Azure',
    'administrateur réseaux infrastructure',
    # Cybersécurité
    'analyste cybersécurité',
    'consultant sécurité RSSI',
    # Produit / Design
    'product manager',
    'UX designer product',
    # ERP / CRM
    'consultant SAP',
    'consultant Salesforce CRM',
    # Architecture
    'architecte logiciel solution',
    # Sales / Marketing / Consulting
    'business developer SaaS',
    'chef de projet IT agile',
    'consultant transformation digitale',
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
                        'category': categorize(r['title'], ''),
                        'daysAgo': indeed_parse_age(r['dateText']),
                        'isESN': is_esn_company(r['company']), 'isCabinet': is_cabinet(r['company']),
                        'source': 'indeed',
                    })
            except Exception as e:
                print(f'  [Indeed] "{kw}" erreur: {e}')
            finally:
                context.close()

            print(f'  [Indeed] "{kw}" +{kw_count} → {len(jobs)} total')

        browser.close()

    return jobs

# ── Collective.work ───────────────────────────────────────────────────────────

CW_BASE     = 'https://www.collective.work'
CW_JOBS_URL = CW_BASE + '/jobs/fr?contractType=Permanent&page={page}'
CW_HEADERS  = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

def _cw_location(proj):
    wp = proj.get('workPreferences') or []
    if isinstance(wp, list):
        wp_str = ' '.join(str(x).lower() for x in wp)
        if 'remote' in wp_str or 'full_remote' in wp_str:
            return 'Remote'
    loc = proj.get('location') or {}
    name = (loc.get('fullNameFrench') or loc.get('fullNameEnglish') or '') if isinstance(loc, dict) else str(loc)
    name = name.lower()
    if not name: return ''
    if 'paris' in name: return 'Paris'
    if 'lyon' in name: return 'Lyon'
    if 'bordeaux' in name: return 'Bordeaux'
    if 'nantes' in name: return 'Nantes'
    if 'toulouse' in name: return 'Toulouse'
    if 'rennes' in name: return 'Rennes'
    if 'montpellier' in name: return 'Montpellier'
    if 'lille' in name: return 'Lille'
    if 'marseille' in name: return 'Marseille'
    if 'strasbourg' in name: return 'Strasbourg'
    if 'grenoble' in name: return 'Grenoble'
    if 'remote' in name or 'télétravail' in name: return 'Remote'
    if 'france' in name: return 'ALL'
    return name.split(',')[0].strip().title()

def fetch_collective(max_pages=12):
    jobs, seen_ids = [], set()
    for page in range(1, max_pages + 1):
        url = CW_JOBS_URL.format(page=page)
        req = urllib.request.Request(url, headers=CW_HEADERS)
        try:
            html = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode('utf-8')
        except Exception as e:
            print(f'  [CW p{page}] erreur: {e}')
            break
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if not m:
            print(f'  [CW p{page}] __NEXT_DATA__ introuvable')
            break
        try:
            data    = json.loads(m.group(1))
            queries = data['props']['pageProps']['dehydratedState']['queries']
            results = queries[0]['state']['data']['results']
            projects   = results.get('projects', [])
            pagination = results.get('pagination', {})
        except Exception as e:
            print(f'  [CW p{page}] parse erreur: {e}')
            break
        if not projects:
            break
        page_count = 0
        for proj in projects:
            job_id = proj.get('id', '')
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            title   = (proj.get('name') or proj.get('sumUp') or '').strip()
            co      = proj.get('company') or {}
            company = (co.get('name') or '').strip() if isinstance(co, dict) else str(co).strip()
            if not title or not company:
                continue
            slug = proj.get('slug', job_id)
            link = f'{CW_BASE}/jobs/fr/{slug}'
            desc = re.sub(r'<[^>]+>', ' ', proj.get('description') or '').strip()[:200]
            try:
                pub = datetime.fromisoformat((proj.get('publishedAt') or '').replace('Z', '+00:00'))
                days = max(0, (datetime.now(timezone.utc) - pub).days)
            except Exception:
                days = 0
            jobs.append({
                'id':        1100000 + len(jobs),
                'title':     title,
                'company':   company,
                'link':      link,
                'desc':      desc,
                'location':  _cw_location(proj),
                'category':  categorize(title, ''),
                'daysAgo':   days,
                'isESN':     is_esn_company(company),
                'isCabinet': is_cabinet(company),
                'source':    'cw',
            })
            page_count += 1
        print(f'  [CW p{page}] {page_count} offres → {len(jobs)} total')
        total = pagination.get('total', 0)
        if page * 30 >= total:
            break
        time.sleep(0.5)
    return jobs

# ── WeLoveDevs ────────────────────────────────────────────────────────────────

WLD_JOBS_URL = ('https://welovedevs.com/fr/app/jobs'
                '?query=&refinementList%5BcontractTypes%5D%5B0%5D=permanent')

def _wld_location(hit):
    loc = hit.get('location') or hit.get('city') or hit.get('place') or ''
    if isinstance(loc, dict):
        loc = loc.get('label') or loc.get('name') or loc.get('city') or ''
    loc = (loc or '').strip().lower()
    if not loc or any(x in loc for x in ['remote','télétravail','teletravail','full remote']):
        return 'Remote'
    if 'paris' in loc: return 'Paris'
    if 'lyon' in loc: return 'Lyon'
    if 'bordeaux' in loc: return 'Bordeaux'
    if 'nantes' in loc: return 'Nantes'
    if 'toulouse' in loc: return 'Toulouse'
    if 'rennes' in loc: return 'Rennes'
    if 'montpellier' in loc: return 'Montpellier'
    if 'lille' in loc: return 'Lille'
    if 'marseille' in loc: return 'Marseille'
    if 'strasbourg' in loc: return 'Strasbourg'
    if 'grenoble' in loc: return 'Grenoble'
    if 'france' in loc: return 'ALL'
    parts = loc.split(',')
    return parts[0].strip().title() if parts[0].strip() else ''

def _wld_days_ago(hit):
    for field in ['publishedAt', 'createdAt', 'updatedAt', 'date', '_highlightResult']:
        val = hit.get(field)
        if not val or field == '_highlightResult':
            continue
        try:
            if isinstance(val, (int, float)):
                ts = val / 1000 if val > 1e10 else val
                pub = datetime.fromtimestamp(ts, tz=timezone.utc)
                return max(0, (datetime.now(timezone.utc) - pub).days)
            if isinstance(val, str):
                pub = datetime.fromisoformat(val.replace('Z', '+00:00'))
                return max(0, (datetime.now(timezone.utc) - pub).days)
        except Exception:
            pass
    return 999  # pas de date → sera éliminé par le filtre global 90j

LJ_BASE = 'https://lesjeudis.com'
LJ_JOBS_URL = LJ_BASE + '/jobs?page={page}'
LJ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

def fetch_lesjeudis(max_pages=15):
    """Scrape LesJeudis CDI jobs via __NEXT_DATA__ (no Playwright needed)."""
    jobs, seen_ids = [], set()
    for page in range(1, max_pages + 1):
        url = LJ_JOBS_URL.format(page=page)
        req = urllib.request.Request(url, headers=LJ_HEADERS)
        try:
            html = urllib.request.urlopen(req, context=ctx, timeout=15).read().decode('utf-8')
        except Exception as e:
            print(f'  LesJeudis page {page} erreur: {e}')
            break
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not m:
            break
        try:
            items = json.loads(m.group(1))['props']['pageProps']['data']['jobs']['pages']
        except Exception as e:
            print(f'  LesJeudis page {page} parse error: {e}')
            break
        if not items:
            break
        for item in items:
            job_id = item.get('id')
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            title   = (item.get('title') or '').strip()
            company = (item.get('organization') or '').strip()
            if not title or not company:
                continue
            url_path = (item.get('url') or {}).get('path') or item.get('urlNoPrefix') or ''
            link = LJ_BASE + url_path if url_path else ''
            if not link:
                continue
            # Published date → daysAgo
            days_ago = 0
            pub_str = item.get('published') or ''
            if pub_str:
                try:
                    pub = datetime.fromisoformat(pub_str)
                    if pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    days_ago = max(0, (datetime.now(timezone.utc) - pub).days)
                except Exception:
                    pass
            # Location
            remote_opts = item.get('remoteOptions') or []
            is_remote = any('télétravail' in (r.get('label') or '').lower() for r in remote_opts)
            if is_remote:
                location = 'Remote'
            else:
                addresses = item.get('address') or []
                loc = next((a for a in addresses if a.lower() not in ('france',)), None)
                location = loc or (addresses[0] if addresses else 'France')
            # Logo
            logo = None
            org = item.get('organizationProfile') or {}
            if org.get('logo'):
                logo = org['logo']
            elif item.get('logo'):
                logo = item['logo']
            jobs.append({
                'id':        1200000 + len(jobs),
                'title':     title,
                'company':   company,
                'link':      link,
                'desc':      '',
                'location':  location,
                'category':  categorize(title, ''),
                'daysAgo':   days_ago,
                'logo':      logo,
                'isESN':     is_esn_company(company),
                'isCabinet': is_cabinet(company),
                'source':    'lj',
            })
        print(f'  Page {page}: {len(items)} jobs (total {len(jobs)})')
        time.sleep(0.5)
    print(f'  LesJeudis: {len(jobs)} CDI récupérés')
    return jobs

# ── Station F ──────────────────────────────────────────────────────────────────
SF_APP_ID  = 'CSEKHVMS53'
SF_API_KEY = 'ZTQzYjA0MGViZWQ5YmU0YWRkMjQ0ODhlYmFiOGNiOTU1MmVmMmExZDFkMDI2MjNmMGExNTA1OTdlMjM4ZDlhN2ZpbHRlcnM9d2Vic2l0ZS5yZWZlcmVuY2UlM0FzdGF0aW9uLWYtam9iLWJvYXJk'
SF_INDEX   = 'wk_cms_jobs_production_careers'
SF_BASE    = 'https://jobs.stationf.co'

def fetch_stationf():
    """Fetch Station F CDI jobs via Algolia API (no Playwright needed)."""
    qs = urllib.parse.urlencode({
        'x-algolia-agent': 'Algolia for JavaScript (3.35.0); Browser (lite)',
        'x-algolia-application-id': SF_APP_ID,
        'x-algolia-api-key': SF_API_KEY,
    })
    url = f'https://{SF_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries?{qs}'

    jobs, seen = [], set()
    page = 0
    nb_pages = 1

    while page < nb_pages:
        hit_params = urllib.parse.urlencode({
            'enableABTest': 'false',
            'query': '',
            'page': page,
            'hitsPerPage': 20,
            'facetFilters': '[["contract_type_names.en:Full-Time"]]',
        })
        payload = json.dumps({'requests': [{'indexName': SF_INDEX, 'params': hit_params}]}).encode()
        req = urllib.request.Request(url, data=payload, method='POST',
                                     headers={'Content-Type': 'application/json'})
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=15)
            result = json.loads(resp.read())['results'][0]
        except Exception as e:
            print(f'  StationF page {page} erreur: {e}')
            break

        if page == 0:
            nb_pages = result.get('nbPages', 1)

        for h in result.get('hits', []):
            oid = h.get('objectID') or h.get('slug', '')
            if not oid or oid in seen:
                continue
            seen.add(oid)

            title   = (h.get('name') or '').strip()
            org     = h.get('organization') or {}
            company = (org.get('name') or '').strip()
            if not title or not company:
                continue

            slug = h.get('slug') or oid
            link = f'{SF_BASE}/jobs/{slug}'

            # Location
            offices = h.get('offices') or []
            remote_val = h.get('remote') or ''
            if remote_val in ('remote', 'fulltime'):
                location = 'Remote'
            elif offices:
                location = offices[0].get('city') or offices[0].get('district') or 'France'
            else:
                location = 'France'

            # Logo
            logo = None
            logo_obj = org.get('logo') or {}
            thumb = logo_obj.get('thumb') or {}
            logo = thumb.get('url') or logo_obj.get('url') or None

            # daysAgo
            days_ago = 0
            pub = h.get('published_at') or ''
            if pub:
                try:
                    dt = datetime.fromisoformat(pub.replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    days_ago = max(0, (datetime.now(timezone.utc) - dt).days)
                except Exception:
                    pass

            jobs.append({
                'id':        1300000 + len(jobs),
                'title':     title,
                'company':   company,
                'link':      link,
                'desc':      '',
                'location':  location,
                'category':  categorize(title, ''),
                'daysAgo':   days_ago,
                'logo':      logo,
                'isESN':     is_esn_company(company),
                'isCabinet': is_cabinet(company),
                'source':    'sf',
            })

        print(f'  StationF page {page+1}/{nb_pages}: {len(result.get("hits",[]))} jobs (total {len(jobs)})')
        page += 1
        if page < nb_pages:
            time.sleep(0.3)

    print(f'  StationF: {len(jobs)} CDI récupérés')
    return jobs

def fetch_wld(max_scroll=10):
    """Scrape WeLoveDevs CDI jobs via Playwright, intercepting Algolia API responses."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('  Playwright non disponible, WeLoveDevs ignoré')
        return []

    hits_raw = []

    def on_response(response):
        if 'algolia' not in response.url:
            return
        if response.status != 200:
            return
        try:
            data = response.json()
            for result in (data.get('results') or [data]):
                for hit in result.get('hits', []):
                    hits_raw.append(hit)
        except Exception:
            pass

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            locale='fr-FR',
            viewport={'width': 1280, 'height': 900},
        )
        page.set_default_navigation_timeout(30000)
        page.set_default_timeout(10000)
        page.on('response', on_response)
        try:
            page.goto(WLD_JOBS_URL, wait_until='domcontentloaded', timeout=30000)
        except Exception as e:
            print(f'  [WLD] chargement erreur: {e}')
            browser.close()
            return []

        # Attendre que les premières requêtes Algolia arrivent
        page.wait_for_timeout(4000)

        # Scroll pour déclencher la pagination infinie
        for _ in range(max_scroll):
            prev = len(hits_raw)
            try:
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1200)
            except Exception:
                break
            if len(hits_raw) == prev:
                break

        browser.close()

    if not hits_raw:
        print('  [WLD] aucun résultat Algolia intercepté')
        return []

    if hits_raw:
        print(f'  [WLD] {len(hits_raw)} hits bruts, fields: {list(hits_raw[0].keys())}')

    jobs, seen_ids = [], set()
    for hit in hits_raw:
        obj_id = str(hit.get('objectID', '') or hit.get('id', ''))
        if not obj_id or obj_id in seen_ids:
            continue
        seen_ids.add(obj_id)

        title = (hit.get('title') or '').strip()
        if not title:
            continue

        # Company in smallCompany.companyName
        sc = hit.get('smallCompany') or {}
        company = (sc.get('companyName') or sc.get('name') or '').strip()
        if not company:
            continue

        # CDI filter
        ct = hit.get('contractTypes') or []
        if isinstance(ct, str): ct = [ct]
        if ct and not any(x.lower() in ('permanent', 'cdi') for x in ct):
            continue

        slug = hit.get('seoAlias') or hit.get('helmetHandle') or obj_id
        link = f'https://welovedevs.com/fr/app/jobs/{slug}'
        places = hit.get('formattedPlaces') or []
        location = _wld_location({'location': places[0] if places else ''})

        jobs.append({
            'id':        1000000 + len(jobs),
            'title':     title,
            'company':   company,
            'link':      link,
            'desc':      (hit.get('descriptionPreview') or '')[:200],
            'location':  location,
            'category':  categorize(title, ''),
            'daysAgo':   _wld_days_ago(hit),
            'isESN':     is_esn_company(company),
            'isCabinet': is_cabinet(company),
            'source':    'wld',
        })

    print(f'  [WLD] {len(jobs)} CDI WeLoveDevs (dédupliqués)')
    return jobs

# ── LinkedIn ──────────────────────────────────────────────────────────────────

LI_GUEST_URL = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
LI_HEADERS   = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'Accept': 'text/html,*/*',
}
LI_KEYWORDS = [
    'développeur', 'software engineer', 'data engineer', 'devops',
    'cloud architect', 'cybersécurité', 'product manager', 'data scientist',
    'fullstack', 'backend developer', 'frontend developer', 'mobile developer',
    'machine learning', 'SRE',
]

def _li_parse_cards(html):
    """Parse LinkedIn job cards from guest API HTML response."""
    jobs_raw = []
    cards = re.findall(r'<li>(.*?)</li>', html, re.DOTALL)
    for c in cards:
        t   = re.search(r'class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>', c, re.DOTALL)
        co  = re.search(r'class="base-search-card__subtitle".*?<a[^>]*>\s*(.*?)\s*</a>', c, re.DOTALL)
        loc = re.search(r'class="job-search-card__location"[^>]*>\s*(.*?)\s*</span>', c, re.DOTALL)
        dt  = re.search(r'datetime="([^"]+)"', c)
        jid = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', c)
        if not (t and co and jid):
            continue
        title   = re.sub(r'<[^>]+>', '', t.group(1)).strip()
        company = re.sub(r'<[^>]+>', '', co.group(1)).strip()
        city    = re.sub(r'<[^>]+>', '', loc.group(1)).strip() if loc else ''
        jobs_raw.append({
            'title':   title,
            'company': company,
            'city':    city,
            'date':    dt.group(1) if dt else '',
            'job_id':  jid.group(1),
        })
    return jobs_raw

def fetch_linkedin(pages_per_kw=3, max_hits=600):
    """Fetch full-time jobs in France from LinkedIn via the public guest API.
    No login required — uses the same endpoint as LinkedIn's public job search.
    f_JT=F → Full-time (closest to CDI on LinkedIn).
    """
    seen_ids, jobs = set(), []

    for kw in LI_KEYWORDS:
        if len(jobs) >= max_hits:
            break
        kw_new = 0
        for page in range(pages_per_kw):
            if len(jobs) >= max_hits:
                break
            url = LI_GUEST_URL + '?' + urllib.parse.urlencode({
                'keywords': kw,
                'location': 'France',
                'f_JT':     'F',      # Full-time
                'start':    str(page * 25),
                'count':    '25',
            })
            req = urllib.request.Request(url, headers=LI_HEADERS)
            try:
                resp = urllib.request.urlopen(req, context=ctx, timeout=15)
                html = resp.read().decode('utf-8', 'replace')
            except Exception as e:
                print(f'  [LI] "{kw}" p{page} erreur: {e}')
                break

            cards = _li_parse_cards(html)
            if not cards:
                break  # no more results

            for c in cards:
                job_id = c['job_id']
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                company = c['company']
                title   = c['title']
                if not company or not title:
                    continue

                # Age from date string
                try:
                    from datetime import datetime, timezone
                    d = datetime.fromisoformat(c['date'])
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=timezone.utc)
                    age = max(0, (datetime.now(timezone.utc) - d).days)
                except Exception:
                    age = 99

                jobs.append({
                    'id':        1300000 + len(jobs),
                    'title':     title,
                    'company':   company,
                    'link':      f'https://www.linkedin.com/jobs/view/{job_id}/',
                    'desc':      '',
                    'location':  ms_normalize_location(c['city'].split(',')[0].strip(), ''),
                    'category':  categorize(title, ''),
                    'daysAgo':   age,
                    'isESN':     is_esn_company(company),
                    'isCabinet': is_cabinet(company),
                    'source':    'li',
                })
                kw_new += 1

            time.sleep(0.5)

        print(f'  [LI] "{kw}" → {kw_new} nouveaux (total {len(jobs)})')
        time.sleep(0.8)

    return jobs

# ── Welcome to the Jungle ─────────────────────────────────────────────────────

WTTJ_ALGOLIA_APP    = 'CSEKHVMS53'
WTTJ_ALGOLIA_KEY    = '4bd8f6215d0cc52b26430765769e65a0'
WTTJ_ALGOLIA_INDEX  = 'wttj_jobs_production_fr'
WTTJ_ALGOLIA_URL    = f'https://{WTTJ_ALGOLIA_APP}-dsn.algolia.net/1/indexes/{WTTJ_ALGOLIA_INDEX}/query'
WTTJ_BASE           = 'https://www.welcometothejungle.com'

WTTJ_KEYWORDS = [
    'développeur', 'ingénieur logiciel', 'data', 'devops', 'cloud',
    'cybersécurité', 'product manager', 'designer', 'fullstack',
    'machine learning', 'sre', 'backend', 'frontend', 'mobile',
]

def _wttj_normalize_location(hit):
    """Extract and normalize location from a WTTJ Algolia hit."""
    remote = hit.get('remote', 'no')
    if remote in ('yes', 'full'):
        return 'Remote'
    offices = hit.get('offices') or []
    if not offices:
        return 'France'
    city = (offices[0].get('city') or '').strip()
    postal = ''  # WTTJ doesn't provide postal code in offices
    return ms_normalize_location(city, postal) if city else 'France'

def _wttj_days_ago(hit):
    date_str = hit.get('published_at', '')
    if not date_str:
        return 99
    try:
        d = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return max(0, (datetime.now(timezone.utc) - d).days)
    except Exception:
        return 99

def fetch_wttj(days=30, max_hits=1000):
    """Fetch CDI jobs from Welcome to the Jungle via their Algolia search API.
    Filters to jobs published in the last `days` days, covering all tech keywords.
    """
    import math
    headers = {
        'Content-Type': 'application/json',
        'X-Algolia-Application-Id': WTTJ_ALGOLIA_APP,
        'X-Algolia-API-Key': WTTJ_ALGOLIA_KEY,
        'Origin': WTTJ_BASE,
        'Referer': WTTJ_BASE + '/fr/jobs',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    # Unix timestamp for `days` ago
    since_ts = int((datetime.now(timezone.utc).timestamp())) - days * 86400

    seen_ids, jobs = set(), []

    for kw in WTTJ_KEYWORDS:
        if len(jobs) >= max_hits:
            break
        page = 0
        while len(jobs) < max_hits:
            body = json.dumps({
                'query': kw,
                'filters': 'contract_type:full_time AND offices.country_code:FR',
                'numericFilters': [f'published_at_timestamp >= {since_ts}'],
                'hitsPerPage': 100,
                'page': page,
                'attributesToRetrieve': [
                    'name', 'organization', 'offices', 'remote',
                    'published_at', 'wk_reference', 'new_profession',
                    'summary', 'objectID',
                ],
            }).encode()
            req = urllib.request.Request(WTTJ_ALGOLIA_URL, data=body, method='POST', headers=headers)
            try:
                resp = urllib.request.urlopen(req, context=ctx, timeout=15)
                data = json.loads(resp.read())
            except Exception as e:
                print(f'  [WTTJ] "{kw}" p{page} erreur: {e}')
                break

            hits = data.get('hits', [])
            nb_pages = data.get('nbPages', 1)
            new_count = 0
            for hit in hits:
                obj_id = hit.get('objectID', '')
                if not obj_id or obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)

                org = hit.get('organization') or {}
                company = (org.get('name') or '').strip()
                if not company:
                    continue

                title = (hit.get('name') or '').strip()
                if not title:
                    continue

                org_slug = (org.get('slug') or '')
                wk_ref   = (hit.get('wk_reference') or '')
                if not org_slug or not wk_ref:
                    continue  # skip jobs without a valid URL
                link = f'{WTTJ_BASE}/fr/companies/{org_slug}/jobs/{wk_ref}'

                profession = (hit.get('new_profession') or {}).get('sub_category_name', '')
                desc = (hit.get('summary') or '')[:200]

                jobs.append({
                    'id':        1200000 + len(jobs),
                    'title':     title,
                    'company':   company,
                    'link':      link,
                    'desc':      desc,
                    'location':  _wttj_normalize_location(hit),
                    'category':  categorize(title, profession),
                    'daysAgo':   _wttj_days_ago(hit),
                    'isESN':     is_esn_company(company),
                    'isCabinet': is_cabinet(company),
                    'source':    'wttj',
                })
                new_count += 1

            print(f'  [WTTJ] "{kw}" p{page}/{nb_pages-1} → {new_count} nouveaux (total {len(jobs)})')
            page += 1
            if page >= nb_pages or not hits:
                break
            time.sleep(0.2)
        time.sleep(0.3)

    return jobs

# ── Logos (Clearbit Autocomplete) ────────────────────────────────────────────

CLEARBIT_AC = 'https://autocomplete.clearbit.com/v1/companies/suggest?query='

def _name_match(query, result_name):
    """Return True if result_name is plausibly the same company as query.
    Uses bidirectional token overlap: shared tokens must represent ≥50% of
    BOTH the query and the result (prevents "Orange" → "Orange County Register").
    """
    STOP = {
        # Formes juridiques
        'sa', 'sas', 'srl', 'sarl', 'inc', 'ltd', 'llc', 'bv', 'gmbh', 'co', 'corp',
        # Articles / conjonctions
        'the', 'de', 'du', 'le', 'la', 'les', 'et', 'and', 'en', 'by',
        # Géo génériques
        'france', 'europe', 'global', 'international', 'worldwide',
        # Mots business ultra-génériques (ne distinguent pas deux entreprises)
        'group', 'groupe', 'holding', 'partners', 'partner', 'associates',
        'services', 'service', 'solutions', 'consulting', 'conseil',
        'management', 'capital', 'invest', 'ventures', 'studio',
        # Tech génériques
        'cloud', 'digital', 'tech', 'technology', 'technologies',
        'software', 'systems', 'data', 'ai', 'it',
    }
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

def enrich_crm(jobs):
    """Add CRM fields to each job: crm_link, is_client, crm_status,
    crm_tc (T&Cs signed), crm_open_job, crm_consultant (paternité).
    All data comes from the weekly cache — no live API calls."""

    if not os.path.exists(CRM_CACHE_FILE) and not RECRUITCRM_TOKEN:
        print('  Token RECRUITCRM absent et pas de cache, enrichissement CRM ignoré')
        for j in jobs:
            j.update({'crm_link':'','is_client':False,'crm_status':'','crm_tc':None,'crm_open_job':False,'crm_consultant':'','crm_last_updated':'','crm_updated_by':''})
        return jobs

    crm_lookup, users = _load_crm_lookup()
    if not crm_lookup:
        for j in jobs:
            j.update({'crm_link':'','is_client':False,'crm_status':'','crm_tc':None,'crm_open_job':False,'crm_consultant':'','crm_last_updated':'','crm_updated_by':''})
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

    matched = clients = prospects = 0
    for j in jobs:
        company = (j.get('company') or '').strip()
        res = match_map.get(company)
        if res:
            j['crm_link']         = res['crm_link']
            j['is_client']        = res['is_client']
            j['crm_status']       = res.get('status', '')
            j['crm_tc']           = res.get('has_tc', None)
            j['crm_open_job']     = res.get('has_open_job', False)
            j['crm_consultant']   = res.get('consultant', '')
            j['crm_last_updated'] = res.get('updated_on', '')
            j['crm_updated_by']   = res.get('updated_by', '')
            matched += 1
            if res['is_client']:                     clients += 1
            elif res.get('status') == 'Prospect':    prospects += 1
        else:
            j.update({'crm_link':'','is_client':False,'crm_status':'','crm_tc':None,'crm_open_job':False,'crm_consultant':'','crm_last_updated':'','crm_updated_by':''})

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

    # Indeed: blocked by cloud IP detection — removed
    # print('Fetch Indeed...')

    print('Fetch Collective.work...')
    try:
        cw = fetch_collective(max_pages=12)
        jobs += cw
        print(f'  {len(cw)} CDI Collective.work')
    except Exception as e:
        print(f'  Collective.work erreur: {e}')

    print('Fetch LesJeudis...')
    try:
        lj = fetch_lesjeudis(max_pages=15)
        jobs += lj
        print(f'  {len(lj)} CDI LesJeudis')
    except Exception as e:
        print(f'  LesJeudis erreur: {e}')

    print('Fetch Station F...')
    try:
        sf = fetch_stationf()
        jobs += sf
        print(f'  {len(sf)} CDI Station F')
    except Exception as e:
        print(f'  Station F erreur: {e}')

    print('Fetch WeLoveDevs...')
    try:
        wld = fetch_wld(max_scroll=10)
        jobs += wld
        print(f'  {len(wld)} CDI WeLoveDevs')
    except Exception as e:
        print(f'  WeLoveDevs erreur: {e}')

    print('Fetch LinkedIn...')
    try:
        li = fetch_linkedin(pages_per_kw=3, max_hits=600)
        jobs += li
        print(f'  {len(li)} offres LinkedIn')
    except Exception as e:
        print(f'  LinkedIn erreur: {e}')

    print('Fetch Welcome to the Jungle...')
    try:
        wttj = fetch_wttj(days=30, max_hits=1000)
        jobs += wttj
        print(f'  {len(wttj)} CDI Welcome to the Jungle')
    except Exception as e:
        print(f'  Welcome to the Jungle erreur: {e}')

    # ── Filtre global : on ne garde que les offres de moins de 90 jours ──────────
    before = len(jobs)
    jobs = [j for j in jobs if j.get('daysAgo', 0) <= 90]
    print(f'Total: {len(jobs)} offres ({before - len(jobs)} supprimées car > 90j)')

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
            j.setdefault('crm_updated_by', '')

    updated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    template = open('template.html', encoding='utf-8').read()
    html = (template
            .replace('__JOBS__', json.dumps(jobs, ensure_ascii=False))
            .replace('"__UPDATED__"', f'"{updated}"'))

    os.makedirs('docs', exist_ok=True)
    open('docs/index.html', 'w', encoding='utf-8').write(html)
    print('docs/index.html généré')
