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
    'job link group','jobglober',
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
    'cgi','safran','thales','shape it','smile group','smile',
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
    # "Open" seul ou "Open Consulting / Open Group / Open Sourcing" — trop court pour substring
    if c == 'open' or c.startswith('open ') or c.endswith(' open'):
        return True
    if ' rh' in c or c.endswith(' rh'):
        return True
    if 'recrutement' in c:
        return True
    return False

def is_esn(company):
    """Compat: renvoie True si cabinet OU ESN (pour backward compat si besoin)."""
    return is_cabinet(company) or is_esn_company(company)

# ── Taille d'entreprise ───────────────────────────────────────────────────────
# Cache croisé : rempli dynamiquement par WTTJ + Station F, puis appliqué
# à toutes les sources. Clé = nom entreprise lowercase.
_company_size_cache: dict = {}

# Valeurs connues pour grandes entreprises fréquentes
KNOWN_COMPANY_SIZES = {
    'capgemini': 350000, 'atos': 90000, 'accenture': 700000,
    'sopra steria': 50000, 'sopra': 50000, 'cgi': 90000,
    'alten': 45000, 'thales': 80000, 'safran': 100000,
    'airbus': 130000, 'orange': 140000, 'sncf': 150000,
    'edf': 160000, 'société générale': 130000, 'societe generale': 130000,
    'bnp paribas': 200000, 'bnp': 200000, 'axa': 150000,
    'crédit agricole': 150000, 'credit agricole': 150000,
    'lvmh': 170000, 'totalenergies': 105000, 'total': 105000,
    'michelin': 120000, 'renault': 110000, 'stellantis': 300000,
    'amazon': 1500000, 'google': 150000, 'meta': 80000,
    'microsoft': 220000, 'apple': 160000, 'ibm': 260000,
    'deloitte': 330000, 'pwc': 280000, 'kpmg': 260000,
    'ernst & young': 365000, 'ey ': 365000,
    'devoteam': 10000, 'wavestone': 3500, 'sqli': 3000,
    'aubay': 8000, 'inetum': 27000, 'scalian': 6000,
    'econocom': 9000, 'akkodis': 50000, 'assystem': 7000,
    'infotel': 2500, 'groupe sii': 7000, 'smile group': 1300, 'smile': 1300,
    # ── HelloWork (4613 entreprises, tous secteurs) ──
    '10 fers serrurerie': 30, '1001 repas': 625, '1001 vies habitat': 3000, '123 pare-brise': 625, '1pact aquitaine': 30,
    '1pact grand-est': 30, '1pact grand-ouest': 3000, '1pact hauts-de-france': 30, '1pact normandie': 30, '1pact occitanie': 30,
    '1pact paris nord': 30, '1pact paris sud-est': 30, '1pact paris sud-ouest': 30, '1pact provence-et-languedoc': 30, '1pact rhône-alpes-ouest': 30,
    '1pact seine-et-marne': 30, '1pact val-de-loire': 30, '20 minutes': 625, '3c.': 625, '3f': 3000,
    '44 materiaux': 30, '6tm': 150, '7eme regiment du materiel': 625, "a l'abri des flots": 30, 'a table !': 20000,
    'a&b couture': 625, 'a.j.p.c': 30, 'a2c contrôle': 150, 'a2ti': 30, 'aalberts hfc comap sa': 625,
    'ab courtage': 150, 'abaka': 30, 'abb france': 20000, 'abbaye – groupe afp': 150, 'abc puériculture': 625,
    'abcde': 30, 'aber propreté': 3000, 'abil': 30, 'abil informatique': 30, 'abil ressources': 30,
    'abm - alliance bois materiel': 30, 'abmi groupe': 625, 'abram distribution': 30, 'abridéal': 150, 'absolis interim nantes': 30,
    'absys cyborg': 625, 'abyss energy': 150, 'ac marca ideal': 150, 'acadomia': 625, 'académie avec': 30,
    'acaly': 150, 'acb': 150, 'accenture france': 20000, 'acceo': 150, 'acces industrie': 625,
    'access work': 30, 'accesud': 30, 'accior': 150, 'accompagnement stratégie maine et loire': 150, 'acd groupe': 625,
    'ace transport': 150, 'acensi': 30, 'acepp': 625, 'acgv services': 150, 'achil': 30,
    'achille bertrand': 30, 'acii by audensiel': 150, 'acr': 150, 'acsent confluences': 150, 'acsent de nouvelle aquitaine': 625,
    'acsent de provence': 625, 'acsent d’armorique': 625, 'acsent sud-ouest': 150, 'actemium bretagne': 150, 'actemium loire océan': 150,
    'actemium maintenance & intégration bordeaux': 625, 'actemium maintenance toulouse': 150, 'actemium marine': 150, 'actemium ndt pes': 150, 'actem’otel': 150,
    'actiale': 150, 'action enfance': 625, 'action france': 7500, 'action france magasins': 20000, 'activ travaux': 150,
    'activus group': 150, 'acto consulting.': 30, 'acto intérim': 150, 'acto intérim médical': 30, 'acton': 30,
    'actua': 150, 'acxes': 150, 'ad doutaves': 30, 'ad neoparts': 7500, 'ad poids lourds': 7500,
    'ad-vantage': 150, 'ad3': 625, 'adagio aparthotel': 3000, "adapei-nouelles côtes d'armor": 3000, 'adapeila': 3000,
    'additi': 625, 'addixgroup': 150, 'adef': 3000, 'adef residences': 150, 'adeis rh': 30,
    'adekma levage': 30, 'ademe': 3000, 'adentis': 625, 'adequasys': 150, 'adequation': 150,
    'adexcel consulting': 30, 'adhap': 3000, 'adhap direct': 3000, 'adhex': 625, 'adhexpharma': 150,
    'adista': 625, 'adjuvoo': 150, 'adm.': 7500, 'adod': 30, 'adoma': 3000,
    'adonis paysages': 30, "adopt'": 3000, 'adr alcen': 150, 'adressepro': 30, 'adroma conseil': 150,
    'advolis orfis': 150, 'adwork’s travail temporaire': 150, 'adx groupe': 625, 'ad’ex ouest': 150, 'aec intérim': 30,
    'aed groupe': 150, 'aema groupe': 20000, 'aerochim fareva': 150, 'aertec': 150, 'aesio santé': 7500,
    'affrais production': 625, 'affretoo': 625, 'afi esca': 150, 'afnor groupe - association française de normalisation': 625, 'afpa': 7500,
    'afpa entreprises': 7500, 'afpi formation et alternance nord pas de calais': 625, 'afpi lyon': 150, 'afyren': 150, 'ag2r la mondiale': 20000,
    'agap2': 3000, 'agap2it': 625, 'agate it': 150, 'agema': 150, 'agence armada': 150,
    'agence france prestige': 30, 'agence regard': 150, 'ages & vie': 3000, 'agesys': 150, 'agglomération du grand saint-dizier, der & vallées': 625,
    'aggreko': 150, 'agh': 625, 'agh consulting': 625, 'agidra': 30, 'agilia technology': 30,
    'aginergy': 150, 'agir graphic': 150, 'agir à dom': 625, 'agpm': 625, 'agregio solutions': 30,
    'agri montauban': 30, 'agri team': 30, 'agrial': 20000, 'agricole - gueudet 1880': 3000, 'agriland': 30,
    'agriplas sotralenz': 150, 'agrisanterre': 150, 'agrivalor': 30, 'agrivia': 150, 'agriwatt': 150,
    'agrizone': 150, 'agro consulting': 625, 'agronutrition': 150, 'agôn electronics': 3000, 'ahg ateliers de la haute garonne': 30,
    'aiguillon construction': 625, 'aircalo': 150, 'aircos': 150, 'airflux': 625, 'airius': 30,
    'airria': 150, 'ais': 625, 'aivancity': 30, 'ajc ingénierie': 30, 'ajr médical': 30,
    'akanea développement': 625, 'akela interim': 150, 'akkodis': 20000, 'aktisea': 150, 'akzo nobel': 20000,
    'alain afflelou': 3000, 'alain milliat': 30, 'alan allman associates': 3000, 'alb conseil': 150, 'alcadia entreprises': 150,
    'alcis transports': 150, 'aldes': 3000, 'alenvi': 30, 'alessia': 30, 'alfa laval france': 20000,
    'alfi': 625, 'alfi association': 150, 'algolia': 150, 'aliantec': 150, 'aliaxis france': 3000,
    'alierys': 30, 'alispharm': 625, 'alithya': 3000, 'alixio group': 625, 'alkera': 3000,
    'alkern': 3000, 'all solutions': 150, 'allanic 56': 30, 'allez energies – groupe allez': 3000, 'alliade habitat': 625,
    'alliance automotive group': 3000, 'alliance des énergies': 30, 'alliance emploi': 3000, 'alliance global procurement': 150, 'alliance healthcare': 3000,
    'alliance vie': 3000, 'allianz': 3000, 'allianz france – aepps': 7500, 'allianz partners': 3000, 'allo plombier services': 30,
    'alloga': 625, 'allopneus': 625, 'almond': 625, 'alpagel': 625, 'alpee': 30,
    'alpes cn': 150, 'alpes contrôles': 625, 'alpha': 625, 'alphatex': 30, 'alphitan': 625,
    'alptis': 625, 'alro transport': 150, 'alsacienne de restauration': 625, 'alsapan': 625, 'alseamar': 150,
    'alstef group': 625, 'alt': 625, 'alta aeroport': 30, 'altam h&r': 150, 'alteca': 625,
    'altelios technology group': 625, 'alten': 20000, 'alterburo': 150, 'alterea': 625, 'altereo': 150,
    'alteresco': 30, "altern'emploi lille": 150, "alternativ'emploi": 150, 'altho': 625, 'altidom': 625,
    'altim': 150, 'altitude infra': 625, 'altitude technique': 30, 'altrad comi poujaud': 625, 'altrad endel': 3000,
    'altrad prezioso': 625, 'am group': 30, 'ama terra – pierre gagnaire': 30, 'amaclio productions': 30, 'amada europe': 7500,
    'amanora technologies': 30, 'amaris group': 150, 'amarris groupe': 625, 'amato': 3000, 'ambition consulting & services': 150,
    'ameg': 150, 'amelis': 625, 'ametra': 625, 'amiltone': 625, 'amk energy': 150,
    'amosan petrochemicals': 30, 'ampi': 150, 'amplitude': 625, 'amrest france': 150, 'amrest kfc': 150,
    'amv': 625, 'anacours': 150, 'anaveo': 625, 'andema': 30, 'andina': 30,
    'andrew staffing': 30, 'andrice': 150, 'andros': 20000, 'anea santé': 30, 'anemos': 625,
    'anett': 3000, 'anfsi': 625, 'angers loire métropole': 625, 'angevin donada': 625, 'angevin entreprise générale bretagne': 625,
    'angevin groupe': 625, 'angevin ile-de-france': 625, 'angevin jaffre': 625, 'angevin lépine tp': 625, 'angevin personnic': 625,
    'angélina': 625, 'animalis': 625, 'anjac health & beauty': 3000, 'annexx': 150, 'ansamble': 3000,
    'antargaz': 3000, 'anthès': 30, 'antigny nutrition': 30, 'antin résidences': 625, 'antoine distribution': 625,
    'ap-hp': 20000, 'apave': 20000, 'apei moselle': 3000, 'apex': 30, 'apf france handicap pays de la loire': 625,
    'api restauration': 20000, 'apivia courtage': 30, 'apixit': 625, 'aplicit': 30, 'apollon - management du sport': 30,
    "appart'city": 3000, 'appiman': 30, 'applexion': 150, 'approtech': 30, 'aprc group': 150,
    'april': 3000, 'aprolia': 150, 'aprolis': 625, 'aprolliance': 3000, 'aprolliance hygiène spécifique': 150,
    'aprolliance sécurité': 625, 'aprr': 3000, 'apst btp 06': 30, 'aptar beauty': 625, 'aptiskills': 625,
    'aqmo': 150, 'aqualeha': 150, 'aqualter': 150, 'aquantis': 30, 'aquitaine réseaux': 30,
    'aramisauto': 625, 'araymond': 625, 'araymond fluid connection': 625, 'arba': 150, 'arc europe': 625,
    'arcelormittal france': 20000, 'arche immobilier & services': 20000, 'arche mc2': 625, 'archipel habitat': 625, 'ard': 150,
    'areas': 7500, 'areas assurances': 3000, 'ares property': 625, 'aresia': 625, 'arev environnement': 30,
    'arial industries': 150, 'ariane group': 7500, 'aristid': 625, 'arjeka': 30, 'arjo': 625,
    'arkadia group': 625, 'arkadia ingenierie': 150, 'arkea banque entreprises et institutionnels': 625, 'arkema': 20000, 'arkeos': 30,
    'arkeup': 30, 'arkose&co': 625, 'arkéa asset managment': 150, 'arkéa financements & services': 625, 'armand thiery': 3000,
    'armatis': 7500, 'armonia': 20000, 'armonys restauration': 150, 'armor group': 3000, 'armorine': 30,
    'armory': 150, "armée de l'air et de l'espace": 20000, 'arnal': 30, 'arnal - résotainer': 30, 'aroma zone | hyteck': 625,
    'arpavie': 3000, 'arpej': 150, 'arpep pays de la loire': 625, 'arpilabe services': 150, 'arpon technologies': 150,
    'arpège': 3000, 'art & fenêtres': 625, 'art industrie': 30, 'art renov': 30, 'artelia': 20000,
    'arteloge': 625, 'artemis group': 3000, 'artemys': 625, 'arthrex france': 150, 'arthus sourcing': 30,
    'arts solutions sarl': 150, 'artus recrutements': 625, 'as fluid': 30, 'as international': 625, 'asa tp': 30,
    'asap.work': 150, 'asartis': 150, 'asca': 30, 'asf restauration': 625, 'asi': 625,
    'asigma': 150, 'askell': 625, 'asobo studio': 625, 'assadia': 3000, 'assistance santé à domicile': 30,
    'association amorce': 30, 'association horizon amitié': 150, 'association hospitalière de bretagne': 3000, 'association parme': 150, 'association saint benoit labre': 625,
    'assu 2000': 625, 'assurance mutuelle des motards': 625, 'assurances crédit mutuel  gie': 3000, 'assurant': 625, 'assureo': 150,
    'assystem': 7500, 'astek': 7500, 'astorm': 30, "astr'in": 625, 'astron': 30,
    'aswo france': 625, 'atalian global services': 20000, 'atalian maintenance et energy': 30, 'atawey sas': 30, 'atelier dalloz lapidaires': 30,
    'atexis': 3000, 'atlagel': 625, 'atlanroute': 150, 'atlantic ingénierie': 625, 'atlantique alimentaire': 150,
    'atlantique automatismes incendie': 625, 'atlantique materiaux': 625, 'atmb': 625, 'atol conseils et développements': 625, 'atol opticiens': 150,
    'atos': 20000, 'atout groupe': 625, 'atouts': 150, 'atral group': 625, 'atyx': 150,
    'au bureau': 3000, 'au fil des marques - vestiti': 625, 'au fil des toits': 30, 'aub santé': 625, 'aubay': 7500,
    'aubert & duval': 3000, 'auchan retail france': 20000, 'audensiel technologies': 3000, 'audex atlantique': 30, 'audi': 625,
    'audi - gueudet 1880': 3000, 'audicer conseil': 150, 'audika': 3000, 'audition marc boulet': 150, 'audition santé': 625,
    'augereau autocars': 150, 'augereau links': 30, 'aures – groupe afp': 625, 'autajon': 3000, 'auto pièces atlantique': 625,
    'auto1 group france': 625, 'auto1.com': 625, 'autodistribution dhenin': 150, 'autodistribution farsy': 150, 'autodistribution pl - saifa nsr': 30,
    'autohero': 150, 'automatique et industrie': 150, "automobile club de l'ouest": 625, 'autonome ensemble - chez jeannette': 30, 'ava6': 150,
    'avanista': 150, 'avenir conseil': 625, 'avenir deconstruction': 625, 'avenir focus': 30, 'avenir rh': 30,
    'avibresse': 30, 'avicars': 150, 'aviko be': 3000, 'avipur': 625, 'avisto': 625,
    'aviva cuisines': 625, 'avril': 7500, 'avril services': 625, 'avs emploi': 30, 'awake': 625,
    'axa banque': 20000, 'axa en france': 20000, 'axa group operations': 7500, 'axa partners': 625, 'axa wealth services': 150,
    'axe informatique': 150, 'axeal': 625, 'axel location': 30, 'axeria iard': 150, 'axians réseaux mobiles privés': 3000,
    'axiome associes': 625, 'axplora': 3000, 'axxes': 625, 'ayvens france': 3000, 'az france': 625,
    'azaleo': 150, 'azaé': 7500, 'azur evasion': 150, 'azura group / disma interational': 20000, 'azureva': 625,
    'aäsgard': 150, 'aéroport de strasbourg entzheim': 150, "aéroports de la côte d'azur": 625, 'aésio mutuelle': 3000, 'b&b hotels': 3000,
    'b-hive': 625, 'b2a laboratoires de biologie médical': 625, 'babcock wanson': 625, 'babilou': 3000, 'babolat': 625,
    'babolat electricité - groupe firalp': 30, 'baby village': 30, 'bacha coffee france': 150, 'badie': 625, 'bagage france luxe': 625,
    'baker tilly': 3000, 'balitrand': 625, 'banana moon': 150, 'banque de savoie': 625, 'banque europeenne du credit mutuel': 625,
    'banque populaire alsace lorraine champagne': 3000, 'banque populaire auvergne rhône alpes': 3000, 'banque populaire bourgogne franche comté': 3000, 'banque populaire grand ouest': 3000, 'banque populaire mediterranée': 3000,
    'banque populaire rives de paris': 3000, 'banque transatlantique': 625, 'barrachin btp': 150, 'barraine immo': 150, 'barrault': 625,
    'barrière': 7500, 'barthelemy manutention': 150, 'bassetti': 625, 'bastide 1880': 150, 'bastide le confort médical': 3000,
    'bat france': 150, 'bati avenue': 30, 'batidoc': 30, 'batimantes': 30, 'batka': 150,
    'baud industries': 625, 'baudin chateauneuf': 3000, 'baudouin': 30, 'baumard 49': 150, 'baume': 150,
    'baxterstorey france': 625, 'baywa r.e. solar distribution': 150, 'bbf réseaux - groupe firalp': 150, 'bbm et associés': 625, 'bcf life sciences': 150,
    'bd corporation': 150, 'bd france': 625, 'bdo': 3000, 'bdor': 30, 'be green group': 150,
    'be ys': 625, 'be ys cloud': 30, 'be ys shared services': 625, 'bechtle france': 625, 'becquet sas': 30,
    'bee engineering': 625, 'behive': 30, 'beissier': 150, 'belambra': 625, 'belle environnement': 150,
    'benefit cosmetics sas': 625, 'beneteau': 3000, 'bentin': 150, 'beraiser': 30, 'berger levrault': 3000,
    'bergerat monnoyeur': 3000, 'berner france': 3000, 'bertin technologies': 625, 'bertrand franchise': 7500, 'bertrand hospitality': 3000,
    'bertrand retail': 20000, 'bessé': 625, 'best western plus ermitage meudon': 150, 'beton solutions mobiles': 150, 'betrec ig': 150,
    'bexley': 150, 'bf assainissement': 30, 'bfc': 150, 'big fernand': 625, 'bigmat': 150,
    'bilfinger nuclear france': 150, 'bimbo qsr': 625, 'bio3g': 625, 'biocoop': 7500, 'biocyte': 150,
    'biofournil': 150, 'biofrais': 150, 'biogaran': 625, 'biogroup': 7500, 'biolandes': 625,
    'biomérieux': 20000, 'bioporc': 150, 'biosynex': 625, 'biotech dental': 625, 'biotrial': 625,
    'bioviver': 150, 'birdz': 150, 'biscotte pasquier andrézieux': 150, 'biscotte pasquier brissac': 625, 'biscotte pasquier fontenay-le-comte': 150,
    'biscotte pasquier saint herblain': 30, 'biscuits fossier': 150, 'bistro yonnais': 150, 'blachere illumination': 150, 'blanchard': 30,
    'blanchisserie de paris': 150, 'blanchisserie du maine': 150, 'blanchon': 625, 'blch': 150, 'blondel sas': 30,
    'bloomind': 30, 'blot': 625, 'blue': 150, 'bluedocker': 150, 'bmi group': 625,
    'bml': 625, 'bmw - gueudet 1880': 30, 'bmw indigo': 150, 'bnp paribas': 20000, 'boas': 30,
    'bocage magasin': 625, 'boccard': 3000, 'bodet': 3000, 'bodet campanaire': 150, 'bodet time et sport': 150,
    'body minute': 150, 'bofrost*france': 625, 'boissinot elevage': 30, 'boncolac traiteur': 625, 'bonduelle': 20000,
    'bonilait': 30, 'bonjours groupe présence 30': 3000, 'bonobo': 30, 'book&pay': 150, 'boplan france': 30,
    'boralex': 625, "bord'o energies": 30, 'borflex': 625, 'bossard sa': 150, 'bosser expertise | comptasanté': 150,
    'boulanger': 7500, 'boulangerie  ange': 3000, 'boulangerie augustin': 625, 'boulangerie louise': 3000, 'boulangerie nehauser sa': 3000,
    'boulangerie tiffanie': 150, 'bourdin paysage': 150, 'boutic auto': 30, 'bouyer leroux': 3000, 'bouygues construction': 20000,
    'bouygues telecom': 7500, 'bpa experts associés': 30, 'bpce infogérance & technologies': 3000, 'bpce sa': 20000, 'bpce solutions informatiques': 3000,
    'bps intérim': 150, 'brand sisters (tara jarmon - zapa)': 625, 'brasserie lancelot': 30, 'bred banque populaire': 7500, 'breizh café': 625,
    'brenntag sa': 625, 'brest métropole habitat': 625, 'bretagne automobiles': 150, 'bretagne manutention': 150, 'bretinov': 30,
    'brico dépôt': 7500, 'bricodealtorro': 30, 'bricoman': 3000, 'bridgestone': 625, 'bridor': 3000,
    'brigade de maintenance': 7500, 'brigade de sapeurs-pompiers de paris': 7500, "brink's": 20000, 'brioche et viennoiserie thomas': 150, 'brioche pasquier': 3000,
    'brioche pasquier aubigny': 625, 'brioche pasquier cerqueux': 625, 'brioche pasquier charancieu': 625, 'brioche pasquier châtelet': 625, 'brioche pasquier etoile': 625,
    'brioches fonteneau': 625, 'britalu': 30, 'brittany ferries': 3000, 'bruce': 30, 'brun invest': 3000,
    'brun sas': 30, 'brunet - ortec group': 625, 'bruno sas': 150, 'bréal': 30, 'bsa - bretagne sud autocars': 150,
    'bst': 150, 'btp consultants': 625, 'bucher municipal': 3000, 'buffalo grill': 7500, 'bugey aintérim belley': 30,
    'bugey aintérim belmont': 30, 'bugey ain’terim': 30, 'bugey ain’terim bellignat': 30, 'building manager': 30, 'bulles de crèches': 150,
    'bunzl france': 3000, 'burban palettes': 625, 'bureau acs': 625, 'bureau veritas': 20000, 'business france': 3000,
    'business k concept': 30, 'business time club': 30, 'but': 7500, 'buty': 30, 'by marie': 30,
    'béné inox': 150, 'c&t consultants': 30, 'c-stock': 150, 'c.b.i.': 150, 'cabinet lecomte': 30,
    'cache cache': 3000, 'caddenz': 150, 'cadec': 30, 'caduceum': 625, 'caf du rhône': 625,
    'cafe joyeux': 625, 'cafpi': 3000, 'cafés malongo': 625, 'cafés richard': 150, 'cairus': 30,
    "caisse d'epargne bourgogne franche comté": 3000, "caisse d'epargne bretagne pays de loire": 3000, "caisse d'epargne grand est europe": 3000, "caisse d'epargne hauts de france": 3000, "caisse d'epargne ile-de-france": 3000,
    "caisse d'epargne languedoc roussillon": 3000, "caisse d'epargne loire drome ardèche": 3000, "caisse d'epargne loire-centre": 3000, "caisse d'epargne normandie": 3000, "caisse d'epargne rhône alpes": 3000,
    'caisse d’epargne côte d’azur': 3000, 'caisse federale de credit mutuel': 20000, 'caisse regionale credit mutuel de normandie': 625, 'caisse regionale credit mutuel ile de france': 3000, 'caisse regionale credit mutuel midi atlantique': 625,
    'caisse regionale credit mutuel savoie-mont blanc': 625, 'caisse regionale de credit mutuel du centre': 3000, 'caisse regionale du credit mutuel dauphine vivarais': 625, 'caisse regionale du credit mutuel massif central': 625, 'caisse regionale du credit mutuel mediterraneen': 3000,
    'came france': 150, 'cameca': 150, 'camozzi materiaux': 150, 'camping-car park': 150, 'campus france': 150,
    'campus pro': 150, 'can': 150, 'canal plus': 20000, 'candia': 3000, 'canon france': 3000,
    'cantin construction': 30, 'cap ingelec': 625, 'cap océan': 3000, 'cap west': 30, 'capa intérim': 30,
    'capcar': 150, 'capeb rhône et grand lyon': 30, 'capeos conseils': 625, 'capex': 30, 'capfinances': 625,
    'capgemini': 20000, 'capgemini shared services': 20000, 'capifrance': 150, 'capri': 30, 'caprisk development': 150,
    'capsis': 30, 'capsum': 150, 'captrain': 625, 'caquant': 30, 'carambar & co': 625,
    'carene assurances': 150, 'cargill': 3000, 'carglass': 3000, 'caroll': 3000, 'carrefour': 20000,
    'carrefour market': 20000, 'cars simplon': 150, 'cartercash': 3000, 'cartonnerie gondardennes': 625, 'casamance': 150,
    'casavo': 150, 'casden banque populaire': 625, 'cash converters': 30, 'cash piscines': 625, 'cash systèmes industrie - csi': 150,
    'cashmag': 150, 'castel freres': 150, 'castorama': 20000, 'castres equipement': 625, 'cathelain': 625,
    'catrybayart': 150, 'cautioneo': 30, 'cavac': 3000, 'cavac biomatériaux': 30, 'cavac distribution - gamm vert': 150,
    'caveo consulting': 30, 'cazam': 30, 'cbre': 3000, 'cbre gws france': 625, 'cbs angers': 30,
    'cbs rouen': 30, 'cbs tours': 30, 'ccas de grenoble': 3000, "cce constructions de la cote d'emeraude": 150, 'cci lyon métropole': 625,
    'cci paris ile-de-france': 3000, 'ccl consulting': 150, 'ccmo mutuelle': 150, 'cdiscount': 3000, 'cea': 20000,
    'cecia': 150, 'cecurity.com': 150, 'ceeri': 30, 'cegelec mobility': 625, 'cegelec renewable energies': 150,
    'cegelec tertiaire idf': 625, 'celad': 3000, 'celencia': 150, 'celetis': 150, 'celfy la manche': 150,
    'celtys': 625, 'ceme': 625, 'ceme aquitaine': 625, 'ceme atlantique': 30, 'ceme centre est': 625,
    'ceme guerin': 625, 'ceme moreau': 150, 'ceme nucléaire': 30, 'censio': 30, 'center parcs': 7500,
    'centre de formation des compagnons du tour de france toulouse': 30, 'centre départemental enfants et familles': 625, 'centre espoir': 625, 'centre eugène marquis': 625, 'centre hospitalier de poitiers': 7500,
    'centre hospitalier guillaume regnier rennes': 3000, 'centre hospitalier leon bourgeois': 3000, 'centre hospitalier prive brest - pasteur': 625, "centre hospitalier prive de l'europe": 625, 'centre hospitalier privé du montgardé': 150,
    'centre hospitalier privé sainte-marie': 625, "centre mco cote d'opale": 625, 'centre orthopedique de dracy-le-fort': 150, 'centre oscar lambret': 625, 'centrimex': 150,
    'century 21': 150, 'cerap prévention': 625, 'cerdys': 150, 'cerfrance brocéliande': 625, "cerfrance côtes d'armor": 625,
    'cerfrance des savoie': 625, 'cerfrance loire': 150, 'cerfrance mayenne/sarthe': 625, 'cerfrance nord pas de calais': 625, 'cerfrance normandie ouest': 625,
    'cerfrance orne': 625, 'cerfrance picardie nord de seine': 625, 'cerfrance poitou-charentes': 625, 'cerfrance rhône & lyon': 625, 'cerfrance seine normandie': 625,
    'cerise et potiron': 625, 'cerp bretagne - atlantique': 3000, 'certis.': 625, 'cesacom': 30, 'cet ingenierie': 150,
    'cetal': 150, 'cetih': 3000, 'cetim': 3000, 'ceva logistics': 20000, 'ceva santé animale': 7500,
    'cezam restauration': 150, 'cfa assifep': 150, 'cfdp assurances': 150, 'cfl cargo france': 150, 'cft - compagnie fluviale de transport': 3000,
    'cft gaz': 3000, 'cgi': 20000, 'cgi finance': 625, 'cgmi': 625, 'cgr': 625,
    'cgworld': 150, 'chabanne': 150, 'chadapaux': 625, 'challancin': 7500, 'champion entreprises': 625,
    'chamtech': 30, 'chanel': 20000, 'channelfret international': 150, "chantiers de l'atlantique": 3000, 'chapel sas': 150,
    'chaplain': 625, 'charier': 150, 'charles christ': 150, 'charpentier tp': 150, 'chateauform': 3000,
    "chauff'eco": 30, 'chausser': 30, 'chausson matériaux': 3000, 'chausséa': 3000, 'chauvin arnoux': 625,
    'chazal': 150, 'chemineau': 625, 'chenue': 150, 'cheops technology': 625, 'chevron oronite sas': 625,
    'chez meunier': 150, "chik'chill": 30, 'chimiget': 625, 'chimirec': 625, 'chocolaterie vincent guerlais': 30,
    'chollet': 150, 'cholton': 150, 'christeyns france': 150, 'chrono flex': 625, 'chronodrive': 20000,
    'chronopost': 3000, 'chu de reims': 7500, 'chu dijon': 7500, 'chu rennes': 7500, 'chubb': 3000,
    'château belmont tours by the crest collection': 30, 'château du portereau': 30, 'cibest groupe': 30, 'cic est': 3000, 'cic lyonnaise de banque': 3000,
    'cic nord ouest': 3000, 'cic ouest': 3000, 'cic sud ouest': 3000, 'cielis': 625, 'ciffreo bona': 3000,
    'cimme manutention': 150, 'cimme sodimat': 150, 'cip automation': 150, 'circet': 3000, 'circet distribution': 625,
    'ciril group': 625, 'citae': 150, 'citaix': 150, 'citame': 3000, 'citroën - gueudet 1880': 3000,
    'citya immobilier': 3000, 'cityz media': 625, 'cité gourmande': 150, 'cité marine': 3000, 'cizeta medicali france': 30,
    'clal saint yvi': 625, 'clarebout': 3000, 'clarens automobiles': 3000, 'clareo lighting': 150, 'clariane': 20000,
    'clarke energy france': 150, 'clayens': 7500, 'cleor': 625, 'clesence amiens': 625, 'climair franceschini': 30,
    'climelec - groupe ceme': 30, 'clinadent': 625, "clinique anne d'artois": 625, 'clinique de chambray les tours': 625, "clinique de la cote d'emeraude": 150,
    'clinique de la region mantaise': 150, 'clinique des 2 caps': 150, 'clinique du parc': 625, 'clinique du sport – bordeaux-mérignac': 150, 'clinique generale': 625,
    'clinique ker yonnec': 150, 'clinique megival': 150, 'clinique notre dame': 150, 'clinique richelieu': 150, 'clinique saint francois': 150,
    'clinique saint germain': 150, 'clinique sainte marie': 150, 'clos des tours – groupe afp': 150, 'clos st roch – groupe afp': 3000, 'club aktif+': 30,
    'club med': 20000, 'clésence': 625, 'cma cgm': 20000, 'cma formation pays de loire': 625, 'cma pays de la loire': 625,
    'cmg conseil': 150, 'cml': 150, 'cmn constructions mécaniques de normandie': 625, 'cmpm': 150, 'cmr': 150,
    'cmt bâtiment': 30, 'cmt génie climatique': 150, 'cnp assurances iard': 3000, 'cnr': 3000, 'cns communications': 150,
    'coallia': 3000, 'coaset': 30, 'coaxis': 150, 'cobat constructions': 625, 'coca-cola europacific partners': 20000,
    'cocerto': 625, 'cocoon': 30, 'cocoonr': 150, 'codeo': 150, 'codimatra': 30,
    'codital france': 30, 'coexya': 625, 'coface': 3000, 'cofel industries': 625, 'cofidis': 3000,
    'cofidis group': 7500, 'cofidur groupe': 625, 'cofigeo': 3000, 'cogebs cee (comptabilité, organisation, gestion basse seine)': 150, 'cogedis': 625,
    'cogelec': 625, 'cogep': 3000, 'cogeparc': 150, 'cohérence': 150, 'coiro tp': 625,
    'colas france': 20000, 'colas rail': 3000, 'colas sa': 20000, 'colis privé': 625, 'collet': 150,
    'colorz': 150, 'colosséum invest': 150, 'columbus': 625, 'com & company': 150, 'comet': 150,
    "communaute d'agglomeration cannes pays de lerins": 625, "communauté d'agglomération du grand annecy": 3000, 'communauté de communes bugey sud': 150, 'commune de fresnes': 3000, 'compagnie de guyenne': 30,
    'compagnie fiduciaire': 625, 'compagnie maritime nantaise - mn': 3000, 'compass group': 20000, 'complétude': 625, 'comptafrance': 625,
    'comptoir des voyages': 150, 'comptoir savoyard de distribution': 625, 'comptoirs richard': 150, 'computacenter': 3000, 'comtat allardet': 150,
    'comtesse du barry': 150, 'concentrix angers': 150, 'concentrix automobile services': 150, 'concentrix caen': 625, 'concentrix chalon sur saône': 625,
    'concentrix compiegne': 3000, 'concentrix fontenay': 150, 'concentrix france': 20000, 'concentrix grand est': 150, 'concentrix montceau': 625,
    'concentrix tourcoing': 625, 'concentrix vitre': 625, 'concept inh': 30, 'concession pad equation': 150, 'concilian': 625,
    'confederation nationale du credit mutuel': 625, 'confiserie du nord': 625, 'confogaz idf': 150, 'conforama france sa': 7500, 'confort et eau': 30,
    'conin-albert': 30, 'connectt': 150, 'conorm': 150, 'conseil departemental de loir et cher': 3000, 'consept ingenierie': 150,
    'conserto': 625, 'conserverie furic': 150, 'conserverie la belle iloise': 625, 'consort group': 3000, 'constructel': 3000,
    'construction dorso': 150, 'consuel': 625, 'consulting technical support': 625, 'consultys': 625, 'contact rh - vienne recrutement': 30,
    'contacts automobiles': 150, 'convivio': 3000, 'cooperl': 7500, 'coopérative u': 20000, 'copas systèmes': 625,
    'copytop': 150, 'cordier by invivo': 20000, 'coris innovation': 150, 'cornoualia': 150, 'cosmeva': 150,
    'cosnet industries': 150, 'costamagna distribution': 625, 'cote sushi': 625, 'cotral lab': 150, 'courtepaille': 3000,
    'covage': 625, 'covap': 150, 'cozynergy': 150, 'cpam lille douai': 625, 'cpm france': 625,
    'cpms': 150, 'cram': 625, 'creatis': 625, 'credit industriel et commercial': 3000, 'credit mutuel asset management': 625,
    'credit mutuel factoring': 625, 'credit mutuel leasing': 625, 'credit mutuel maine-anjou basse-normandie': 3000, 'creditjob': 30, 'creocean': 150,
    'crescendo': 30, 'crescendo restauration': 3000, 'crisalid': 30, 'cristal habitat': 150, 'cristal union': 3000,
    "cristal'id": 150, 'crma aero repair': 625, 'croix-rouge française': 20000, 'cromology': 3000, 'crosscall': 150,
    'crous bretagne': 625, 'crowe': 3000, 'crpcen': 150, 'crédit agricole alpes provence': 3000, 'crédit agricole assurances': 7500,
    'crédit agricole brie picardie': 3000, 'crédit agricole centre france': 3000, 'crédit agricole centre-est': 3000, 'crédit agricole champagne bourgogne': 3000, "crédit agricole d'ile de france": 3000,
    "crédit agricole d'ille et vilaine": 3000, "crédit agricole des côtes d'armor": 3000, 'crédit agricole des régions du centre': 7500, 'crédit agricole des savoie': 3000, 'crédit agricole du finistère': 3000,
    'crédit agricole du languedoc': 3000, 'crédit agricole du morbihan': 3000, 'crédit agricole du nord est': 3000, 'crédit agricole en bretagne': 3000, 'crédit agricole franche-comté': 3000,
    'crédit agricole loire haute-loire': 3000, 'crédit agricole lorraine': 3000, 'crédit agricole nord de france': 3000, 'crédit agricole nord midi pyrénées': 3000, 'crédit agricole normandie': 3000,
    'crédit agricole normandie seine': 3000, "crédit agricole provence côte d'azur": 3000, 'crédit agricole sud méditerranée': 625, 'crédit agricole sud rhône alpes': 3000, 'crédit conseil de france': 150,
    'crédit coopératif': 3000, 'crédit foncier': 625, 'crédit mutuel': 625, 'crédit mutuel alliance fédérale': 20000, 'crédit mutuel arkea': 20000,
    'crédit mutuel de bretagne': 3000, 'crédit mutuel du sud ouest': 625, 'crédit mutuel immobilier': 625, 'crédit mutuel nord europe': 3000, 'crédit mutuel océan': 3000,
    'créer consultants': 30, 'crêperie jarnoux': 150, "crêperie leguen - groupe mix' buffet": 30, 'csm groupe': 150, 'cstb': 625,
    'ct infodream': 30, 'ct ingenierie': 3000, 'ct ingénierie nantes': 625, 'ct ingénierie paris': 625, 'ct ingénierie sud est': 150,
    'ct ingénierie toulouse': 625, 'ct mer forte': 625, 'ctcv tp': 30, 'cth': 625, 'cti': 30,
    'ctp environnement group': 150, 'cuisinella': 3000, 'culligan': 3000, 'curae lab': 150, 'curtil': 150,
    'cv développement': 150, 'cva ipec': 625, 'cve': 625, 'cybermaker': 30, 'cyclife digital solutions': 30,
    'cyclife engineering': 150, 'cyclife france': 625, 'cyrisea': 30, 'cyrus industrie': 30, 'cèdres industries': 625,
    'côte': 150, "côte d'azur habitat": 625, 'côte ouest hôtel': 150, 'côté fenêtres': 150, 'd medica': 625,
    "d'aucy france": 625, "d'aucy locminé": 625, 'd.i.v': 30, 'd2m': 30, 'dachser france': 3000,
    'dacia - gueudet 1880': 3000, 'dafy': 625, 'daher': 20000, 'daikin': 625, 'daimler truck retail': 625,
    'daligault': 30, 'dalkia': 20000, 'dalkia air solutions': 150, 'dalkia electrotechnics': 625, 'dalkia en': 625,
    'dalkia froid solutions': 3000, 'damotte genie climatique': 30, 'dani alu': 150, 'daniel moquet': 30, 'daniel moquet signe vos allées': 30,
    'daniel moquet signe vos clôtures': 30, 'daniel moquet signe vos jardins': 30, 'darty': 20000, 'darwin partners': 150, 'datacorp': 30,
    'datadess': 150, 'datanumia': 150, 'dauchez': 150, 'daum': 150, 'daunat': 3000,
    'dauphiblanc provence': 30, 'dauphiné isolation environnement': 625, 'davidson consulting': 3000, 'davricourt': 625, 'dayuse': 150,
    'db group': 30, 'db schenker': 7500, 'dba groupe': 625, 'dc expansion': 625, "dcf direction des systèmes d'information": 20000,
    'dcs easyware': 625, 'de boislaville - jardins piscines spas': 30, 'de dietrich france semur': 150, 'de père en fils': 30, 'deca propreté': 3000,
    'declic immo': 30, 'def': 3000, 'degauchy tp': 150, 'degrif sport - s2k73': 150, 'degriffstock': 150,
    'deichmann': 20000, 'dekra france': 3000, 'del arte': 3000, 'delabie': 625, 'delagree': 30,
    'delahaye industries': 150, 'delane si': 625, 'delannoy dewailly': 150, 'delauzun': 30, 'delestrez - gueudet 1880': 30,
    'delko': 625, 'delpeyrat': 3000, 'delpharm': 7500, 'delta cafés france': 150, 'delta marketing': 30,
    'delta plus': 3000, 'delta service location': 150, 'deltech': 30, 'delzongle midi-pyrénées': 30, 'demathieu bard': 3000,
    'demathieu bard immobilier': 150, 'demgy': 625, 'demosten': 625, 'demouy': 150, 'den.bzh': 625,
    'den.bzh 22': 625, 'den.bzh 35': 625, 'denios': 625, 'denis materiaux': 625, 'denjean finance': 30,
    'denjean groupe': 625, 'denjean logistique': 625, 'dentego': 3000, 'deodis': 625, 'departement de seine et marne': 3000,
    "departement du val d'oise": 3000, 'deret': 3000, 'deret logistique': 30, 'derichebourg aeronautics services': 20000, 'derichebourg energie': 625,
    'derichebourg interim': 625, 'derichebourg multiservices': 20000, 'desamais groupe findis': 30, 'desautel': 3000, 'descamps bois': 150,
    'descours & cabaud': 20000, 'desenfans': 625, 'dessaigne': 30, 'devatech': 30, 'devglass': 625,
    'dexis': 20000, 'dfm': 625, 'dhl express france': 3000, 'diamantor investissement': 150, 'diana hotels collection': 150,
    'diehl metering': 3000, 'digisap solutions': 150, 'digital realty': 3000, 'dimeo energie': 150, 'dimood group': 625,
    'dimos': 150, 'diot-siaci': 3000, 'dip ascenseurs - fermetures et mobilité': 30, 'dip sa': 30, 'direct assurance': 3000,
    'direction des approvisionnements – dcf': 20000, 'direction des solidarités de la ville de paris': 7500, 'dirickx industries': 625, 'dirickx services': 625, 'dispam': 625,
    'dispro': 150, 'disrok': 30, 'distel': 150, 'distri cash accessoires': 625, 'distriartisan': 30,
    'districenter': 3000, 'dmd': 625, 'dmf': 150, 'dms': 30, 'docali': 150,
    'docaposte': 7500, 'docaret': 150, 'doit platinium': 150, 'domafrais': 30, 'domaine du ferret': 30,
    'domaliance': 3000, 'domea': 150, 'domicile clean': 3000, 'domiserve': 150, 'domitile': 30,
    'domitys': 3000, 'domofrance': 625, 'domusvi': 20000, 'doras': 625, 'dormakaba': 625,
    'dorthz': 30, 'douceurs jacquemart': 30, 'douillet': 30, 'dpd france': 3000, 'dreyfus': 20000,
    'dron': 150, 'drt': 3000, 'ds - gueudet 1880': 30, 'ds restauration': 625, 'ds rhône alpes': 625,
    'dsd organisation': 150, 'dso': 150, 'dsv': 20000, 'dubois menuiserie': 625, 'dune energie': 30,
    'duo santé': 30, 'dupessey&co': 625, 'dupont avec un thé': 30, 'dupuy': 30, 'duqueine group': 625,
    'durand services': 150, 'dv group': 625, 'dyka': 625, 'dynabuy': 30, 'dynaren': 150,
    'délifrance': 3000, 'département de la charente maritime': 3000, 'département des hauts-de-seine': 3000, 'département du val de marne': 7500, 'département syndical': 625,
    'dômes pharma': 625, "e'nergys": 625, 'e.leclerc': 20000, 'e2m': 150, 'e2ts': 625,
    'easy service informatique': 150, 'easydis': 3000, 'eaton': 20000, "eau d'azur": 625, 'eau de paris': 625,
    'eau du grand lyon': 625, 'eau du ponant': 625, 'eau seine & bièvre': 150, 'ebaki': 150, 'ebs emballage': 150,
    'ebtrans france': 3000, 'eccs': 625, 'eckes granini': 3000, 'eclor boissons': 625, 'eclor entreprises': 625,
    'ecm': 625, 'econocom': 7500, 'ecotec - ecologie economie technologie': 30, 'ecotoit': 30, 'ecovigne': 30,
    'ecovrac': 30, 'ecr environnement': 625, 'eden park': 150, 'edenred': 3000, 'edf': 20000,
    'edf power solutions': 3000, 'edf solutions solaires': 3000, 'edieyes': 30, 'edilians': 3000, 'ediser': 150,
    'edl': 150, 'educazen': 30, 'edvance': 3000, 'edycem': 625, 'effektiv': 30,
    'effia': 625, 'efficience santé au travail': 625, 'efficity': 150, 'efht': 30, 'efi automotive': 625,
    'efluid': 150, 'efmh paris - tourisme et hôtellerie': 30, 'efor group': 3000, 'efrapo': 150, 'efs - métiers technicien': 7500,
    'efs etablissement français du sang': 7500, 'egi': 150, 'egis  groupe': 20000, 'eiffage concessions': 20000, 'eiffage construction': 20000,
    'eiffage energie systèmes': 20000, 'eiffage génie civil, eiffage métal': 20000, 'eiffage route': 20000, 'eimi': 625, 'ekium': 3000,
    'ekkiden': 150, 'ekosport': 625, 'ekwateur': 150, 'elan cité': 30, 'elancia': 150,
    'elcia': 150, 'elcimaï': 625, 'electricité de strasbourg': 3000, 'elektron berlin': 150, 'elevance': 30,
    'elex': 625, 'elio & franck': 30, 'elior': 20000, 'elior santé': 20000, 'elis': 20000,
    'eliteam': 150, 'elitel réseaux': 150, 'elivia': 3000, 'ellisphere': 625, 'elsys design': 3000,
    'elyamaje': 30, 'elypse autos': 625, 'elysee cosmétiques': 150, 'eléphant bleu - groupe hypromat': 150, 'emalec': 625,
    'emcd - data & marketing': 30, 'emeis': 20000, 'emeraude solaire miniac-morvan': 150, 'emeria': 625, 'emeria switzerland': 625,
    'emil frey holding agri': 20000, 'emile maurin': 30, 'emile maurin eléments standard mécaniques': 150, 'emile maurin fixation': 150, 'emis': 150,
    'emisys': 625, 'emitech groupe': 150, 'emmanuel maurin': 625, 'emmi desserts france': 3000, 'emoa mutuelle du var': 150,
    'en direct de nos producteurs': 7500, 'endress hauser': 20000, 'endress+hauser': 20000, 'endrix': 625, 'enerchoice france sas': 150,
    'energeo technologies': 30, 'energie et services de seyssel': 150, 'energies france': 150, 'energis rh': 150, 'energy dynamics': 625,
    'eneria': 625, 'enersteel': 150, 'engel & völkers france': 30, 'engie': 20000, 'engit': 150,
    'eni plenitude france s.a.s': 625, 'enilive': 150, 'enogia': 30, 'enova consulting': 150, 'ensmi - ecole nationale supérieure du management immobilier': 30,
    'enspé btp': 625, 'entech': 150, 'enterprise mobility': 20000, 'entremont': 3000, 'entrepose echafaudages': 625,
    'entreprise menuiseries aménagements - ema': 30, 'entreprise pilet': 30, "envie d'oeufs sud est": 30, 'envoyé spécial': 150, 'enygea': 625,
    'enyom distribution - size factory': 150, 'eoda realisations': 30, 'eol group': 150, 'eolen': 30, 'eolya': 150,
    'eowin': 625, 'ep2c energy': 625, 'epackpro': 150, 'epalia': 625, 'epc groupe': 3000,
    'epdc': 30, "epfif (etablissement public foncier d'île-de-france)": 150, 'epi': 150, 'epide - etablissement pour l’insertion dans l’emploi': 3000, 'epigone': 30,
    'epnak': 3000, 'epsa': 3000, 'epsa innovation': 150, 'eqiom': 3000, 'equalia': 625,
    'equans france': 20000, 'equasens': 3000, 'equideos': 150, 'eram magasin': 625, 'eram siège': 625,
    'eramet': 20000, 'erec technologies - groupe firalp': 150, 'erilia': 3000, 'ermitage – groupe afp': 625, 'eryma sas': 625,
    'erys sécurité': 150, 'esccot': 150, 'esli redon : ecole supérieure de logistique industrielle': 30, 'espace agri': 30, 'espacil': 625,
    'esr groupe': 150, 'essentiel & domicile': 625, 'esset pm': 625, 'essity': 20000, 'esso': 3000,
    'est ensemble habitat': 625, 'est métropole habitat': 625, 'est ouvrages': 30, 'estella consulting': 150, 'estella mobility': 150,
    'esti : ecole supérieure des technologies industrielles': 30, 'etablissement de santé la martinière - association jean lachenaud': 150, 'etablissement public de santé mentale (epsm) de la marne': 3000, 'etablissement sainte marie puy de dôme - allier': 20000, 'etchart - industrie de matériaux et revalorisation': 625,
    'etchart - service aux collectivités': 625, 'etchart construction': 625, 'etchart tp': 625, 'etci': 150, 'eternity systems': 625,
    'etesia sas | groupe wolf france': 625, 'etex france': 20000, 'etf': 3000, 'ethis rh': 30, 'eti': 30,
    'etik assurance': 150, 'etlin service frais': 150, 'etna (école des technologies numériques avancées)': 30, 'ets guillet frères': 30, 'ettic': 30,
    'eurasante': 150, 'eureden': 7500, 'eureka éducation': 3000, 'euretudes travail temporaire': 30, 'eurex': 625,
    'eurexo': 625, 'eurial': 7500, 'euridis': 150, 'euro energies': 30, 'euro information': 625,
    'euro station services': 30, 'eurocombles by opnr': 625, 'eurocoop express': 150, 'eurofeu': 3000, 'eurofins biologie medicale': 150,
    'euromaster': 3000, 'europe snacks': 3000, 'europe technologies': 625, 'european camping group': 3000, 'european homes': 150,
    'europorte': 625, 'eurosérum': 625, 'eurovia délégation centre-est': 20000, 'eurovia délégation centre-ouest': 20000, 'eurowipes': 150,
    'even agri': 7500, 'everial france': 625, 'everwin': 150, 'eviden': 3000, 'evolis': 625,
    'evolupharm': 30, 'evoriel': 3000, 'evs professionnel': 150, 'ewigo': 150, 'exail': 3000,
    'exalt': 3000, 'excelvision': 625, 'exco': 3000, 'exens solutions': 150, 'exoceth consulting': 30,
    'experis france': 3000, 'experteam': 150, 'expleo': 20000, 'expliseat': 150, 'express du froid': 30,
    'expresso service': 150, 'extenbois': 30, 'externatic': 30, 'extia': 3000, 'extia ingénierie': 625,
    'extruplast': 150, 'exxact robotics': 150, 'exxelia': 3000, 'eynard robin': 150, 'ezia': 30,
    'f2o': 30, 'fab group': 150, 'fab’academy du pôle formation – uimm (rh)': 150, 'factofrance sas': 150, 'factoria': 625,
    'faculte des metiers – campus de rennes': 150, 'faguo': 150, 'fair’belle': 150, 'faiveleytech': 625, 'family sphere hyères': 150,
    'family sphere toulon': 7500, 'fareneït énergies': 30, 'fareva amboise': 20000, 'fareva farmea': 625, 'fareva pau': 625,
    'faubourg immobilier': 30, 'faubourg promotion': 30, 'fayat batiment': 3000, 'fayat energies services': 3000, 'fayat entreprise tp': 625,
    'fayat fondations': 625, 'fayat groupe': 20000, 'fayat it': 150, 'fayat metal': 3000, 'fayolle': 3000,
    'fb solution': 150, 'fcai': 150, 'fcn': 625, 'fdsea conseil': 625, 'fedd': 150,
    'federation apajh': 3000, 'fedex': 625, 'feelinks': 30, 'fehr': 625, 'felder group france': 150,
    'fenetrea': 625, 'fenwick-linde': 3000, 'fer-play': 150, 'ferguss': 150, 'ferlay': 3000,
    'fermiers du sud-ouest': 625, 'ferrero france commerciale': 3000, 'fetis group': 625, 'feu vert': 3000, 'feuillette eure et loir': 150,
    'feuillette gravigny': 30, 'feuillette troyes': 150, 'feuillette vernouillet': 625, 'fgr': 625, 'ficamex': 150,
    'fichet group': 625, 'fidelia assistance – groupe covéa': 3000, 'fiderim deux savoie': 150, 'fiderim lyon': 150, 'fiducial': 20000,
    'filhet allard': 3000, 'filhet allard maritime': 150, 'filieris': 3000, 'filière travaux publics - eau': 625, 'fill up média': 150,
    'finance people': 30, 'finvens': 150, 'first stop ayme': 3000, 'fiteco': 3000, 'fitness park': 3000,
    'fitnessboutique': 150, 'fives groupe': 7500, 'fizzy': 150, 'flamino': 30, 'flauraud': 625,
    'fleet services group': 150, 'fleurance nature': 150, 'fleury michon': 3000, 'flexcity': 150, 'flexirub': 30,
    'florajet': 30, 'florence dore groupe': 625, 'florette': 3000, 'florimond desprez': 3000, 'fluiconnecto by manuli': 625,
    'flunch': 3000, 'flunch traiteur': 7500, 'fly it': 30, 'fm logistic corporate': 20000, 'fm logistic france': 20000,
    'fmb': 150, 'fnac': 20000, 'fnac darty': 20000, 'focus recrutement': 30, 'fokus': 150,
    'foncia': 20000, 'fondasol': 625, 'fondation aralis': 150, 'fondation bompard': 150, 'fondation casip': 625,
    "fondation des amis de l'atelier": 3000, 'fondation georges boissel': 625, 'fondation innovation et transitions': 30, 'fondation la vie au grand air i priorité enfance': 3000, 'fondation ove': 3000,
    'fondation saint jean de dieu': 3000, 'foodiz groupe': 625, 'foodles': 625, 'forafrance': 150, 'forgital dembiermont': 150,
    'formaposte sud-est': 30, 'forsitec': 30, 'forstaff': 30, 'fortify': 30, 'fortify hr partners': 150,
    'fortil group': 3000, 'fortuneo': 625, "forval (groupement d'employeurs)": 150, 'forvia': 20000, 'forvis mazars': 20000,
    'foselev': 3000, 'fountain': 150, 'fournier retail': 625, 'fpee': 625, 'fraikin': 3000,
    'framatome': 20000, 'francap': 30, 'france air': 625, 'france air export': 625, 'france detection service': 150,
    'france environnement': 150, 'france expert bâtiment': 30, 'france frais rhône-alpes': 150, 'france frais.': 30, 'france galop': 625,
    'france menuisiers': 150, 'france oxygène': 625, 'france sécurité': 625, "france terre d'asile": 3000, 'france volet': 150,
    'franchise camif habitat': 150, 'francofa eurodis': 150, 'franfinance': 625, 'franprix - magasins': 625, 'frans bonhomme': 3000,
    'frans bonhomme chausson tp': 3000, 'free dom': 625, 'free go ouest': 150, 'fregate aero': 625, 'fresenius medical care': 625,
    'fresh.': 3000, 'frial': 625, 'froid climatisation techniques': 150, 'fromi': 150, 'fruisy': 30,
    'frégate aero sud': 150, 'frégate energie': 30, 'ftl group': 150, 'fédération cami sport et cancer': 150, 'fédération française du bâtiment': 150,
    'förch': 3000, 'g truck - gueudet 1880': 3000, 'g-sys': 30, 'g. cartier technologies': 150, 'g7 taxi services': 150,
    'gabopla': 30, 'gac software': 150, 'gagneraud construction': 625, 'gagneraud construction région normandie': 625, 'gagneraud construction région paca': 625,
    'gagneraud construction siège': 3000, 'gaillard pâtissier': 150, 'galapagos gourmet': 625, 'galeries bartoux': 150, 'galeries lafayette': 20000,
    'galliance': 3000, 'galloo france': 625, 'galzin gourmet': 150, 'gamm vert': 3000, 'gamm vert - groupe oxyane': 3000,
    'gan assurances': 3000, 'gan assurances agences': 3000, 'gan patrimoine': 625, 'gan prévoyance': 625, 'ganil': 150,
    'gap référencement': 30, 'garage aubree': 150, 'garden arrosage': 30, 'garden environnement': 30, 'gas bijoux': 150,
    'gascogne': 625, 'gascogne bois': 625, 'gascogne papier': 625, 'gastronomie service': 150, 'gaudu': 30,
    'gbh': 20000, 'gcatrans': 7500, 'ge healthcare': 20000, 'ge séquano': 150, 'geccilor': 150,
    'geco assurances': 625, 'geiq avenir et handicap': 30, 'geiq btp 37': 30, 'geiq impact': 30, 'geiq industrie 21': 30,
    'geiq tl paca': 30, 'geiq tl vdl': 30, 'gel 43': 30, 'gelagri': 625, 'genavir': 625,
    'gendreau conserverie': 625, 'general transmissions': 150, 'generali  assurance': 3000, 'generali assurance': 20000, 'generali france': 20000,
    'genes diffusion': 625, 'genia': 150, "genie climatique de l'est": 625, 'gentle mates': 30, 'genwaves': 150,
    'geo bretagne sud': 30, 'geodis': 20000, 'geofit': 3000, 'georges blanc sas': 625, 'geph': 30,
    'gerama': 150, 'gerard perrier industrie': 3000, 'gerflor': 3000, 'gesec': 30, 'geser best': 150,
    'gest (holding groupe lafourcade)': 625, 'getec': 30, 'getinge france': 20000, 'gfp_tech': 150, 'ggp auto': 3000,
    'ghistelinck lille': 150, 'gie axa': 20000, 'gie even distribution': 7500, 'gie groupe even': 150, 'gie logirep logistic': 3000,
    'gie performance': 150, 'gie sesam-vitale': 150, 'gif emploi': 150, 'gifi': 7500, 'gifi réseau': 7500,
    'gineys': 625, 'girardon materiaux': 625, 'gironde spécialités': 30, 'girpi': 150, 'glaces des alpes': 150,
    'globalis btp': 30, 'gmba&co': 625, 'gmd eurocast': 3000, 'gmf assurances – groupe covéa': 7500, 'gms gestion marketing stratégie': 625,
    'go&live group': 150, 'gofo france': 150, 'golden tulip la baule': 30, 'golden tulip pornic suites': 30, 'golgemma': 30,
    'gonnin duris': 150, 'good job': 30, 'goyard-pôle artisanal': 3000, 'gozoki': 150, 'gozoki frais': 30,
    'gozoki occitanie – cœur d’aveyron': 30, 'gozoki occitanie – pêcheries occitanes': 30, 'gozoki occitanie – traiteur du val de cère': 30, 'goûters magiques': 625, 'gr': 30,
    'gramari - groupe firalp': 150, 'grand frais boucherie': 150, 'grand frais caisses': 150, 'grand frais epicerie': 150, 'grand frais le primeur et le fromager': 3000,
    'grand large yachting': 625, 'grandlyon habitat': 625, 'grands moulins de paris': 3000, 'grandvision': 3000, 'graphitech': 30,
    'grdf': 20000, 'green style': 150, 'greenyard frozen france': 625, 'grenke location': 150, 'grimaud frères': 625,
    'grisot services': 150, 'grit games': 30, 'grosseron': 150, 'groupama centre atlantique': 3000, 'groupama centre manche': 3000,
    "groupama d'oc": 3000, 'groupama gan vie': 3000, 'groupama loire bretagne': 3000, 'groupama méditerranée': 3000, 'groupama nord est': 3000,
    'groupama paris val de loire': 3000, 'groupama rhône alpes auvergne': 3000, 'groupe a2com': 150, 'groupe actu': 625, 'groupe adenes': 3000,
    'groupe adf': 3000, 'groupe adinfo': 150, 'groupe adp': 20000, 'groupe adré': 625, 'groupe adsn': 625,
    'groupe advenis': 625, 'groupe adène': 625, 'groupe afume': 150, 'groupe agrica': 625, 'groupe aim': 150,
    'groupe alainé': 3000, 'groupe albaron': 150, 'groupe alliance': 150, 'groupe alphadoz': 30, 'groupe alphalink': 150,
    'groupe apb': 30, 'groupe apicil': 3000, 'groupe arla': 150, 'groupe armor process industrie (api)': 150, 'groupe atlantic': 20000,
    'groupe audeo': 625, 'groupe autosphere': 7500, 'groupe avem': 3000, 'groupe bage': 625, 'groupe balas': 625,
    'groupe bam': 625, 'groupe bardec': 150, 'groupe barillet': 625, 'groupe barkene': 625, 'groupe baudaire': 3000,
    'groupe bayle': 625, 'groupe bbl': 3000, 'groupe bds': 150, 'groupe beaumanoir': 20000, 'groupe beaumarly': 3000,
    'groupe bernard': 3000, 'groupe bernier': 3000, 'groupe bert': 3000, 'groupe berto': 7500, 'groupe betem': 625,
    'groupe bigard': 20000, 'groupe biscuits bouvard': 3000, 'groupe blanchard': 625, 'groupe bmv': 3000, 'groupe brangeon': 3000,
    'groupe briand': 3000, 'groupe buckler security': 625, 'groupe cahors': 3000, 'groupe can': 625, 'groupe carso': 625,
    'groupe casino': 20000, 'groupe cat': 7500, 'groupe cerba healthcare': 20000, 'groupe charlet': 150, 'groupe chatel': 30,
    'groupe chopard': 3000, 'groupe cisn': 150, 'groupe citizen can': 30, 'groupe cobredia': 3000, 'groupe cofaq': 150,
    'groupe combronde': 3000, 'groupe cooperatif sicarev': 3000, 'groupe coriance': 625, 'groupe courtin': 150, 'groupe covéa': 20000,
    'groupe cpl': 625, 'groupe crystal': 625, 'groupe créative': 625, "groupe d'oeuvres sociales de belleville": 150, 'groupe dallard': 150,
    'groupe david': 150, 'groupe de restauration': 30, 'groupe delineo': 625, 'groupe deret': 3000, 'groupe deux fleuves': 625,
    'groupe diego': 150, 'groupe dubreuil': 7500, 'groupe dubreuil services': 150, 'groupe duclos': 150, 'groupe duval': 7500,
    'groupe editor': 625, 'groupe efire': 150, 'groupe ej': 625, 'groupe elva': 625, 'groupe emera': 3000,
    'groupe emosia': 625, 'groupe empruntis': 625, 'groupe eram': 7500, 'groupe etam': 3000, 'groupe etchart': 3000,
    'groupe excent': 625, 'groupe fareneit': 625, 'groupe fareneït - ecotep': 30, 'groupe fareneït - lg siemac': 30, 'groupe fareneït – alfaklima': 30,
    'groupe fareneït – deltaklima': 30, 'groupe fareneït – exerce': 30, 'groupe fareneït – heliom': 30, 'groupe fareneït – seca': 30, 'groupe fareneït – seem': 30,
    'groupe fareneït – serely': 30, 'groupe fareneït – setelec': 30, 'groupe fareneït – sn koch': 30, 'groupe fauché': 3000, 'groupe faurie': 3000,
    'groupe fdsea 51': 625, 'groupe findis': 625, 'groupe firalp': 3000, 'groupe fleurus': 625, 'groupe foure lagadec': 3000,
    'groupe fournier': 3000, 'groupe franaud': 150, 'groupe france mutuelle': 150, 'groupe france textile production': 30, 'groupe funecap': 3000,
    'groupe gestal': 625, 'groupe giboire': 625, 'groupe gorrias mercedes benz': 150, 'groupe gp': 625, 'groupe gpa': 625,
    'groupe grenat': 30, 'groupe grimaud': 625, 'groupe gth': 625, 'groupe guinier': 625, 'groupe guisnel': 625,
    'groupe hamecher': 625, 'groupe hemmerlin': 625, 'groupe heppner': 3000, 'groupe hmc': 150, 'groupe human immobilier': 3000,
    'groupe idec': 625, 'groupe idec ingenierie': 150, 'groupe igf': 30, 'groupe ima': 7500, 'groupe imestia': 150,
    'groupe interway': 625, 'groupe intuis': 625, 'groupe ipi': 625, 'groupe ixio': 150, 'groupe janneau': 625,
    'groupe jarny': 150, "groupe jean floc'h": 3000, 'groupe jlc': 150, 'groupe joel lefevre': 150, 'groupe keran': 625,
    'groupe kermarrec': 150, 'groupe kertrucks': 625, 'groupe la française': 150, 'groupe lacta traite et lacta proflex': 30, 'groupe lagarrigue': 625,
    'groupe lamotte': 625, 'groupe lancien': 150, 'groupe laure': 625, 'groupe le duff': 20000, 'groupe le triangle': 625,
    'groupe legendre': 3000, 'groupe legrand': 625, 'groupe les comptoirs du monde': 150, 'groupe lhoro agest': 150, 'groupe logis hôtels': 20000,
    'groupe loiseleur': 625, 'groupe louange': 625, 'groupe lucas': 625, 'groupe léa nature': 625, 'groupe m': 3000,
    'groupe m.t.a': 625, 'groupe maine': 625, 'groupe marc': 3000, 'groupe martin belaysoud': 3000, 'groupe materne - mont blanc': 625,
    'groupe mentor': 3000, 'groupe millet industrie': 625, 'groupe mobiliteam': 625, 'groupe modema agri': 150, 'groupe montana': 150,
    'groupe moos': 150, 'groupe mousset': 3000, 'groupe mutualia': 625, 'groupe niort': 625, 'groupe noemys': 625,
    'groupe onet': 20000, 'groupe opnr': 625, 'groupe orain': 625, 'groupe osmaia': 3000, 'groupe oxyane': 3000,
    'groupe oxygène': 150, 'groupe pandora': 150, 'groupe papin': 625, 'groupe paredes orapi': 625, 'groupe parera': 3000,
    'groupe parlym': 3000, 'groupe partouche': 3000, 'groupe pasteur mutualité': 625, 'groupe payant': 625, 'groupe perin': 150,
    'groupe pernat': 625, 'groupe pharea': 150, 'groupe philippe marraud': 625, 'groupe pichet': 3000, 'groupe pilote': 625,
    'groupe piment': 150, 'groupe piveteaubois': 3000, 'groupe plenetude': 150, 'groupe plus (poids lourd utilitaire services)': 150, 'groupe poisson': 625,
    'groupe polylogis': 3000, "groupe pomona - relais d'or": 150, 'groupe pompac développement & comafranc': 7500, 'groupe poullain': 150, 'groupe povataj constructions': 625,
    'groupe promotrans': 625, 'groupe q-park france': 625, 'groupe qualiconsult': 3000, 'groupe queguiner': 3000, 'groupe qérys': 625,
    'groupe rainbow partners': 3000, 'groupe rd': 150, 'groupe rds': 625, 'groupe restalliance': 3000, 'groupe ridoret': 625,
    'groupe rm developpement': 625, 'groupe rose': 625, 'groupe rossi aéro': 625, 'groupe roullier': 7500, 'groupe ruban bleu': 30,
    'groupe résonance imagerie': 625, 'groupe salaün': 625, 'groupe samse': 7500, 'groupe save': 30, 'groupe savoy': 625,
    'groupe scael': 625, 'groupe schiever': 7500, 'groupe schroll': 625, 'groupe sdi': 150, 'groupe seb': 20000,
    'groupe serindus': 625, 'groupe setin': 625, 'groupe sgp': 3000, 'groupe sherwin williams': 20000, 'groupe sia': 625,
    'groupe siat': 625, 'groupe sigma': 625, 'groupe signorizza': 625, 'groupe sii': 20000, 'groupe smb': 150,
    'groupe soflux': 625, 'groupe sorelec': 150, 'groupe sos': 20000, 'groupe sterne': 3000, 'groupe sushi shop': 3000,
    'groupe tanguy matériaux': 3000, 'groupe tds – hospitality & conciergerie': 150, 'groupe technic-assistance': 150, 'groupe thivolle': 625, 'groupe tisserin': 625,
    'groupe titel holding': 625, 'groupe tolomei': 3000, 'groupe tomel': 150, 'groupe trigones': 150, 'groupe trouillet': 625,
    'groupe télégramme': 3000, 'groupe valeor': 625, 'groupe valority': 625, 'groupe verbaere automobile': 625, 'groupe vilavi': 3000,
    'groupe vilogia': 3000, 'groupe zephyr': 7500, 'groupement apogées': 150, 'groupement des hôpitaux de l’institut catholique de lille (ghicl)': 3000, 'groupement des hôpitaux de l’institut catholique de lille - ghicl': 3000,
    "groupement interprofessionnel européen d'assurances (giea)": 30, 'groupement mousquetaires': 20000, 'groupement mousquetaires – agromousquetaires': 30, 'groupement mousquetaires – intermarché': 625, 'gs1 france': 150,
    'gsa healthcare': 625, 'gse': 625, 'gsf': 20000, 'gsi by foncia': 150, 'gsvi': 625,
    'gt logistics': 3000, 'gt solutions': 3000, 'gtp': 30, 'guegan': 30, 'guestadom': 30,
    'gueudet 1880': 3000, 'gueudet pr - gueudet 1880': 3000, 'guilmot gaudais sas': 150, 'guiraud': 150, 'guy hoquet': 3000,
    'guy lefebvre sas': 150, 'guyot environnement': 625, 'gys': 625, 'gémo': 3000, 'gémo siège': 3000,
    'génollière – groupe afp': 3000, 'générale des services': 3000, 'génération': 3000, 'géolithe': 150, 'géométrie variable': 30,
    'h-tube': 625, 'h2air': 150, 'habitat 77': 625, 'habitation moderne': 150, 'had nice & région': 150,
    'hager': 20000, 'halton': 3000, 'hana group': 7500, 'handynamic': 150, 'happ': 30,
    'happy curl - la boutique du coiffeur': 3000, 'hardis group': 3000, 'haribo': 7500, 'harmonie mutuelle': 7500, 'haropa port': 3000,
    'hasap': 625, 'haulotte': 3000, 'haut-de-seine habitat oph': 625, 'havana it & apps': 150, 'havea': 625,
    'haxe direct': 150, 'hays': 625, 'hcl le foyer design': 30, 'hedis': 625, 'hedon technologies': 150,
    'heintz immobilier & hôtellerie': 150, 'heliatec': 150, 'helios': 150, 'hello paris': 150, 'hellofresh': 150,
    'hellowork group': 625, 'helpline': 3000, 'helzear': 30, 'hemea': 150, 'henaff': 150,
    'henry': 150, 'henry desjonquères industries': 150, 'henry schein france sca': 625, 'hensoldt en france': 625, 'hentges': 625,
    'herakles': 30, 'herbarom laboratoire': 30, 'hercules thrustmaster sas': 150, 'herige': 3000, 'hero ambérieu': 30,
    'hero expert': 30, 'herve thermique': 3000, 'hervouet france': 150, 'hes': 30, 'hess automobile': 3000,
    'heverett group': 625, 'hexanet': 150, 'hexatel': 625, 'hexcel': 20000, 'heytens': 150,
    'hiflow': 150, 'highco': 625, 'hih développement': 150, 'hilti france': 3000, 'hippopotamus': 3000,
    'hirsch': 150, 'hirsch group': 625, "histoire d'or": 7500, 'hively hospitality': 3000, 'hm.clause - groupe limagrain': 3000,
    'hn services': 3000, 'hoist finance': 150, 'holding bernard': 150, 'holenek ingénierie': 30, 'holwegweber europe': 150,
    'home life': 30, 'homeserve': 3000, 'hopital la porte verte': 625, 'hopital prive de la baie': 625, 'hopital prive du confluent': 20000,
    'hopital prive nord parisien': 625, 'hoppen': 625, "horizon l'agence de loisir": 30, 'hormann france sa': 150, 'horoquartz': 625,
    'horus conseils': 30, 'hospi grand ouest': 3000, 'house of aby': 3000, 'howdens': 625, 'hoyez sas': 150,
    'hozelock exel': 150, 'hpg invest': 625, 'hr link': 625, 'hubcycle': 30, 'human immobilier': 3000,
    'human location': 30, 'humann & taconet': 150, 'hunteed': 30, 'hunteed recrutement': 30, 'hunteo': 30,
    'hunyvers limoges': 150, 'hunyvers niort aérodrome': 30, 'hunyvers niort mendes': 150, 'hunyvers sa': 625, 'hunyvers soyaux le petureau': 30,
    'huttopia': 3000, 'hydralians': 20000, 'hydro': 625, 'hydrostadium': 150, 'hygena': 30,
    'hynamics': 30, 'hypharm': 150, 'hyphen biomed': 150, 'hypérion développement': 625, 'häagen-dazs arras': 625,
    'hénéo': 150, 'hôpital de riaumont (groupe ahnac)': 625, 'hôpital la musse': 625, 'hôpital privé de l’eure': 625, 'hôpital villiers-saint-denis': 625,
    'hôpitaux paris saint joseph et marie lannelongue': 3000, 'hôpitaux privés rennais - cesson-sévigné': 625, 'hôpitaux privés rennais - saint-grégoire': 625, 'hôtel bleu': 30, 'hôtel dame des arts': 30,
    'hôtel ibis styles': 20000, 'hôtel le galice': 30, 'hôtel le saint antoine.': 30, 'hôtel le sévigné': 30, 'hôtel liautaud': 30,
    'hôtel lyon métropole': 150, 'hôtel mercure la roche sur yon': 150, 'hôtel saint christophe': 30, 'iad': 150, "ibis styles & budget les sables d'olonne": 30,
    'icademie': 150, 'icd international': 30, 'icone automation': 30, 'icoopa': 150, 'icts france': 3000,
    'id automation': 150, 'id logistics': 20000, 'idea informatique': 30, 'idec': 150, 'idec agro & factory': 30,
    'idec grand sud': 30, 'idec hautes technologies': 150, 'idec sante': 150, 'idemia ist': 3000, 'idex': 7500,
    'idkids': 7500, 'iel développement': 30, 'iel exploitation': 30, 'iem paris - ressources humaines': 30, 'iepc': 625,
    'ieseg': 625, 'ifae accueil': 150, 'ifae business school': 150, 'ifae rh': 150, 'ifae santé': 150,
    'ifb france': 150, 'ifcv': 3000, 'ifremer': 3000, 'igam': 625, 'igo solutions': 625,
    'ikigaï': 30, 'ikos': 3000, 'il basilico': 30, 'iliade consulting': 150, 'illicado illi & co': 150,
    'illico travaux': 30, 'im projet': 150, 'ima protect solutions': 150, 'imaginéa': 625, 'imalogie': 30,
    'imc': 30, 'immo city holding': 150, 'immobanques': 150, 'immosens sas': 30, 'impac ingenierie': 625,
    'impec nettoyage': 150, 'imperator industries': 150, 'implid': 625, 'imporelec': 150, 'impresa pizzarotti': 150,
    'impulse ingénierie': 30, 'imv technologies': 625, 'in extenso': 7500, 'in genium': 30, "in'li aura": 150,
    "in'terpech": 150, 'industisol': 150, 'industrie cartarie tronchetti france': 625, "industrielle de contrôle et d'equipement": 150, 'indépendance royale': 150,
    'inedi': 150, 'inelys': 30, 'ineris': 625, 'inetum': 20000, 'infinite orbits': 150,
    'infogene': 625, 'infotel': 3000, 'ingeliance technologies': 625, 'ingeniance': 150, 'ingeva': 625,
    'ingram micro': 625, 'ingénierie techniques d’extinction': 30, 'ingérop': 3000, 'inicea': 7500, 'initia.': 30,
    'initial': 30, 'initiatives dmp': 150, 'inkipio': 30, 'inmac': 625, 'innokka': 30,
    'innolation': 30, 'innotec france': 150, 'innova solutions': 150, 'innoval': 3000, 'inolya': 625,
    'inoxa': 150, 'inrae transfert.': 150, 'inside': 625, "institut de cancérologie de l'ouest": 3000, 'institut de cancérologie de lorraine': 625,
    'institut lyfe': 625, 'institut pasteur': 3000, 'intech': 625, 'intelcia': 3000, 'intelia': 30,
    'inter mutuelles habitat - imh': 625, 'interaction': 3000, 'interdigital': 30, 'interflora': 625, 'interimed - caen': 30,
    'interra log': 30, 'interra pro': 30, 'intersport': 20000, 'interstis': 30, 'intm': 3000,
    'intrum': 625, 'intrum corporate': 625, 'intwee emploi': 30, 'intérim qualité le havre': 30, 'intérim sans frontières': 30,
    'inustry': 30, 'invivo ag° corporate': 3000, 'invivo digital factory': 150, 'invivo group': 7500, 'ioc': 150,
    'ionis education group': 3000, 'ionisos': 150, 'iota group': 625, 'ipc': 150, 'ipp': 30,
    'ippon technologies': 625, 'ippudo paris': 150, 'iqanto': 625, 'iqeq france': 150, 'iqera': 625,
    'ircem': 625, 'iris messidor': 30, 'irisolaris': 625, 'irp auto': 625, 'irt jules verne': 150,
    'isagri': 3000, 'isalys': 150, 'iscod': 30, 'iserba': 625, 'isi intérim': 30,
    'isigny sainte mère': 3000, 'isme': 150, 'it link': 625, 'it-newvision': 150, 'itancia': 625,
    'itas': 625, 'itesoft': 150, 'itga': 625, 'itma': 30, 'itron holding france': 7500,
    'its services': 3000, 'itson': 150, 'ivacom': 30, 'ivc evidensia': 3000, 'iveco': 3000,
    'ividata life sciences': 150, 'ivt security': 150, 'izencia insight': 150, 'izi confort': 3000, 'izimmo by arkea': 150,
    'izipizi': 150, 'iziwork': 625, 'jacadi': 625, 'jack & jones': 150, 'jacques laurent': 30,
    'jacquet-brossard - groupe limagrain': 3000, 'jantesaluservices': 30, 'janvier labs': 625, 'jardiland': 7500, 'jarnot': 30,
    'jc fiolet transports': 150, 'jcdecaux': 3000, 'jd sports': 3000, 'jdc': 3000, 'jean et lisette': 30,
    'jean hue & socoda': 150, 'jean lain mobilité': 3000, 'jean rouyer automobiles': 3000, 'jeanne marguerite – groupe afp': 625, 'jeantil': 150,
    'jeld wen': 625, 'jems': 625, 'jh industries': 625, 'jiliti': 625, 'jk-technic': 30,
    'jlg services': 625, 'joa': 3000, 'job & box': 150, 'job concept': 30, 'job concept alby-sur-chéran': 30,
    'job concept saint-pierre-en-faucigny': 625, 'job medical': 30, 'job&talent': 625, 'jober group': 30, 'jogam': 625,
    'jogam set': 625, 'john cockerill': 7500, 'jott': 625, 'joya': 625, 'jti': 150,
    'juignedis - auchan': 150, 'jung sas': 30, 'jungheinrich': 3000, 'juridica': 625, "jus de fruits d'alsace": 625,
    'jv ageniaa': 30, 'jysk': 20000, 'kaefer': 3000, 'kairnial': 150, 'kaizen solutions': 625,
    'kalhyge': 3000, 'kameo interim': 30, 'kanoma': 150, 'karavel groupe': 3000, 'kardham': 625,
    'katchme': 30, 'kaufler': 30, 'kbane': 625, 'kd distribution': 30, 'keep cool': 625,
    'keep cool franchise': 625, 'kel quartier': 30, 'kelio': 625, 'kellal maintenance': 150, 'keller williams performance': 150,
    'kem one': 3000, 'keolis atlantique': 625, 'keolis bourgogne': 20000, 'keolis courriers du midi': 30, 'keolis gironde': 625,
    'keolis nord': 625, "keolis pays d'aix": 625, 'keolis pays des volcans': 20000, 'keolis rennes métropole': 3000, 'keolis santé': 30,
    'keolis sud allier': 20000, 'keolis sud lorraine': 625, 'keolis trois frontières': 20000, 'keon': 150, 'keredes': 150,
    'kereis france': 625, 'kerhis': 150, 'kerlink': 150, 'kermarrec entreprise': 150, 'kermarrec habitation': 150,
    'kermarrec promotion': 150, 'kermené': 3000, 'kerr france': 30, 'kersia': 3000, 'kertrucks': 625,
    'kertrucks pneus': 150, 'keyence': 625, 'khea concept': 150, 'kia - gueudet 1880': 3000, 'kiko': 3000,
    'kiloutou': 3000, 'king jouet recrutement': 3000, 'kinougarde': 625, 'klee group': 625, 'klesia': 3000,
    'kley': 150, 'koesio aquitaine': 625, 'koesio aura': 625, 'koesio centre est': 150, 'koesio data solutions': 150,
    'koesio est': 150, 'koesio idf': 150, 'koesio managed services': 150, 'koesio mediterranee': 150, 'koesio nord ouest': 150,
    'koesio occitanie': 150, 'koesio paca': 150, 'koncept': 150, 'kone': 3000, 'konica minolta': 3000,
    'koord': 150, 'korian': 20000, 'kp linpac': 625, 'kpmg': 7500, 'krill': 150,
    'ksb': 3000, 'kärcher sas': 625, "l'agence nationale des fréquences": 625, "l'auxiliaire": 625, "l'entrepôt du bricolage": 3000,
    "l'etincelle rh": 30, "l'incroyable": 30, "l'occitane": 7500, "l'oeuf de nos villages": 625, "l'école française": 150,
    'l-expert-comptable.com': 150, 'l-omega': 3000, 'la boulangerie du marché': 625, 'la brigade de buyer': 625, 'la cage': 3000,
    'la casa de las carcasas': 625, 'la celtique': 150, 'la centrale de financement': 625, 'la closerie des lilas': 150, 'la compagnie des pruneaux': 30,
    'la coopérative welcoop': 3000, 'la cravate solidaire': 30, 'la croissanterie': 30, "la côte et l'arête": 625, 'la fabrique des métiers': 30,
    'la famille': 150, 'la fermière': 150, 'la france mutualiste': 625, 'la française des plastiques': 625, "la fruitière d'arbusigny": 30,
    'la halle': 7500, 'la maison bleue': 3000, 'la maison de pilou': 150, 'la maison des charcutiers': 20000, 'la maison des travaux': 625,
    'la maison du sol': 150, 'la manufacture': 150, 'la mie câline': 3000, 'la monnaie de paris siege': 625, 'la mut’': 625,
    "la p'tite boulangerie": 150, 'la parisienne': 150, 'la poste groupe': 20000, 'la pyrénéenne': 3000, 'la redoute france': 3000,
    "la régie de l'eau grand paris sud": 150, "la société les jardins d'arcadie": 3000, 'la solive': 150, 'la tarte tropezienne': 150, 'la tete dans les nuages': 150,
    'labeyrie fine foods': 3000, 'labo france': 625, 'labogena': 30, 'labor hako': 150, 'laboratoire aguettant.': 625,
    'laboratoire arrow': 625, 'laboratoire marque verte': 30, 'laboratoire performance habitat, lph': 30, 'laboratoire rivadis': 150, 'laboratoire svr': 625,
    'laboratoires biové (groupe inovet)': 150, 'laboratoires gilbert': 625, 'laboratoires humeau': 150, 'laboutiqueofficielle.com': 150, 'lacroix défense': 625,
    'lactalis': 20000, 'lactamat': 30, 'lafarge france': 20000, 'lafitte groupe': 150, 'lagardère travel retail': 20000,
    'lahaye global logistics': 3000, 'laita': 3000, 'laiterie de montaigu': 150, 'lajus': 625, 'lamaison.fr': 3000,
    'lamotte gestion transaction': 625, 'lamotte maisons individuelles': 625, 'lamy': 3000, 'lancaster': 625, 'laplace': 625,
    'larcher services': 30, 'larivière': 625, 'laser emploi auvergne': 30, 'lassarat': 625, 'laulade – groupe afp': 625,
    'lavance': 625, 'lbl travel retail': 625, 'lca construction bois': 150, 'lci group nord': 150, 'ld travocean': 150,
    'ldc groupe': 20000, 'lde': 150, 'ldo conseils': 150, 'le cabrh': 30, 'le castel beau site': 30,
    'le ciem': 150, 'le domaine – groupe afp': 625, 'le doré materiaux': 625, 'le du': 625, 'le du hydro-energies-préfa': 150,
    'le du réseaux': 150, 'le finistère assurance': 150, 'le froid pecomark': 625, 'le groupe jardel': 3000, 'le groupe septeo': 3000,
    "le jardin d'acclimatation": 150, 'le jardin de rabelais': 625, 'le lunetier du sud': 30, 'le monde des crêpes': 150, 'le pain du gone': 150,
    'le pavillon des entreprises': 30, 'le roy logistique': 625, 'leaf ingenierie': 150, 'leasecom': 150, 'ledger': 150,
    'legallais': 3000, 'legalplace': 625, 'lego': 20000, 'lelievre immobilier': 150, 'lely center groupe blanchard recrutement': 150,
    'lendys': 150, 'lenoir': 30, 'leo resto': 3000, 'leroy merlin': 20000, 'les assurances mutuelles de picardie': 150,
    'les ateliers grandis': 3000, 'les belles années': 150, 'les bougies de charroux': 150, 'les chaussures bessec': 150, "les clés de l'atelier": 30,
    'les compagnons du devoir': 3000, 'les crudettes': 625, 'les ecoles de la construction durable par saint-gobain': 20000, 'les fermiers du sud-est': 625, 'les grands chais de france': 3000,
    "les jardins de l'anjou": 30, 'les maisons du voyage': 150, 'les maîtres laitiers du cotentin': 625, 'les petites canailles': 625, 'les petits chaperons rouges': 7500,
    'les pierres de frontenac': 30, 'les rapides du poitou': 150, "les secrets d'honoré": 30, 'les serres recrutement': 625, 'les sherpas': 150,
    'les tables mousset': 150, 'les zelles': 625, 'les éleveurs de la charentonne': 150, 'lesieur': 625, 'leyton france': 3000,
    'lgm': 3000, 'lgm ingénierie': 150, 'lh & tech': 30, 'lheureux': 625, 'liane rh': 30,
    'libellio': 30, 'libertium': 150, 'libertium ouest': 625, 'libertium rennes': 30, 'lidl': 20000,
    'liebherr components': 625, 'liebherr mining': 625, 'liebherr-aerospace toulouse': 3000, 'ligartis': 150, 'lightbody europe': 3000,
    'liins': 30, 'lille métropole habitat': 625, 'lily toques': 30, 'limagrain': 7500, 'limagrain coop': 7500,
    'limagrain europe': 3000, 'limagrain ingredients': 625, 'lindab': 150, 'link financial': 150, 'linkeo.com': 625,
    'linking talents': 150, 'linkt': 625, 'linéa propreté': 625, 'lip recrute pour lip': 625, 'litt': 625,
    "liv - laboratoire d'innovation végétale": 30, 'livementor': 150, 'lm5p - le mouton à 5 pattes': 30, 'lmc eurocold': 30, 'lna santé': 7500,
    'lne': 625, 'lobby-privé.com': 30, 'loc maria': 150, 'loc maria biscuits': 150, 'locadour - locarhone': 150,
    'local.fr': 625, 'lodgis': 150, 'lodipat dispat': 30, 'logi ports shuttle': 3000, 'logirep': 3000,
    'logista france': 625, 'logista hometech': 3000, 'logista retail': 625, 'logwire consulting': 150, 'logéal immobilière': 150,
    'loire ocean manutention': 150, 'loison sas': 150, 'lojelis': 150, 'lorflex': 150, 'louis dreyfus armateurs': 3000,
    'louis pion / galeries - lafayette royal quartz': 625, 'loxam': 20000, 'loyez woessen': 150, 'lp art': 150, 'lp charpente': 150,
    'lpg systems': 625, 'lr technologies': 150, 'lr technologies grand ouest': 625, 'lr technologies groupe': 625, 'lr technologies rhône-alpes': 30,
    'lr technologies sud est': 625, 'lr technologies sud ouest': 150, 'lsdh': 3000, 'lsi': 150, 'lubexcel': 150,
    'lucien georgelin': 150, 'lumicene': 30, 'lustucru premium groupe': 625, 'luxe talent': 30, 'luxium solutions': 625,
    'luxury of retail': 625, 'lx france': 150, 'lyreco': 3000, 'léo et associés': 30, 'léon': 3000,
    'lùkla': 625, 'l’agence télécom': 150, 'l’hôtel et spa le richelieu': 30, 'm&m militzer & munch': 625, 'm&s strategy': 150,
    'm+matériaux': 625, 'm- energy - groupe evole energies': 625, 'm-energies': 625, 'm-energies exploitation': 625, 'm-energies service': 150,
    'm.v.r materiaux': 150, 'm3': 150, 'ma chance moi aussi': 150, 'ma-geo': 150, 'maaf assurances – groupe covéa': 7500,
    'mabéo industries': 625, 'macc': 150, 'macif': 20000, 'macsf': 3000, 'mademoiselle de margaux': 30,
    'madic digital': 150, 'madic elec': 150, 'madic group': 3000, 'madic industries': 625, 'mae technologies': 150,
    'maestria': 30, 'maf - mutuelle des architectes français': 625, 'magasins vert - point vert': 150, 'maif': 7500, 'main-forte': 30,
    'mainco': 150, 'mainfreight': 20000, 'maintel sud-est': 150, "mairie d'issy-les-moulineaux": 3000, 'mairie de montbéliard': 625,
    'mairie de puteaux': 3000, 'mairie de savigny sur orge': 625, 'mairie de villejuif': 3000, 'maisadour': 3000, 'maison 123': 7500,
    'maison briau': 150, 'maison chancerelle': 625, 'maison charles perroud': 625, 'maison du frais': 30, 'maison et services': 30,
    'maison kayser': 625, 'maison loraine': 150, 'maison nicolas': 150, 'maison notre dame de philerme - ordre de malte france': 30, 'maison options': 625,
    'maison pradier': 150, 'maison sauvat & cie': 150, 'maison thiriet': 3000, 'maisons & cités': 625, 'maisons du monde': 7500,
    'maisons mca': 625, 'maisons mtb': 30, 'maisons pierre': 625, 'maisons sic': 150, 'maisonsûr': 150,
    'maitres jacques': 150, 'major 5': 30, 'malakoff humanis': 7500, 'malrieu': 625, 'manaero': 150,
    'managing': 30, 'manda': 150, 'mango': 20000, 'manitou group': 3000, 'manorga': 625,
    'manpower': 3000, 'mantu': 20000, 'manuland': 150, 'mapa': 625, 'mapei': 625,
    'marc orian': 7500, 'marc schubel sas': 150, 'marceau': 30, 'marco polo performance': 150, 'marco vasco': 150,
    'marfret': 150, 'marianne international': 625, 'maritima': 3000, 'marsoliler': 30, 'martenat': 625,
    'martenat bretagne': 150, 'martenat sud bretagne': 30, 'martin': 30, 'martin brower': 625, 'marvesting': 3000,
    'mary': 3000, 'mas seeds': 625, 'maser engineering': 625, 'masson': 150, 'master industrie': 150,
    'mastergrid': 625, 'matawan services': 150, 'maten': 150, 'matmut': 7500, 'matrelec': 30,
    'maty': 625, 'mauffrey': 3000, 'maury transports': 625, 'max digital services': 30, 'maxance': 150,
    'maxi zoo': 3000, 'maxicoffee': 3000, 'maximo': 3000, 'maya collection': 625, 'mazet-mercier sas': 150,
    'mba mutuelle': 150, 'mbda': 20000, 'mbsc ikks': 625, 'mc2': 150, 'mca groupe': 150,
    'mccormick retail services': 3000, "mcdonald's": 20000, "mcdonald's france": 20000, 'mci': 3000, 'mcvpap': 150,
    'mda': 625, 'me group': 3000, 'meca diffusion': 30, 'mecapole occitanie': 150, 'mecatechnic': 150,
    'mecatlantic': 30, 'mecavea': 30, 'meccanocar': 150, 'mediaco': 3000, 'mediaco vrac': 150,
    'medimat': 625, 'meent': 30, 'meilleurtaux': 3000, 'mellow yellow magasin': 30, 'mellow yellow siège': 30,
    'menbat': 150, 'menco': 150, 'menlog': 150, 'menuiserie moreau': 150, 'meogroup': 625,
    'mequisa': 150, 'merci jérôme': 30, 'merciplus': 150, 'mercuria': 150, 'mericq sas': 625,
    'merieux nutrisciences silliker': 3000, 'meritis': 625, 'mersch & schmitz': 625, 'mersen': 7500, 'messer france': 625,
    'mestre': 625, 'metaline': 625, 'metro france': 7500, 'metsys': 625, 'mettler toledo': 20000,
    'mewa': 7500, 'mg tech': 150, 'mgefi': 625, 'mgen': 20000, 'mgi digital technology': 150,
    'mi recrutement': 30, 'michael paetzold': 150, 'michaud chailly': 150, 'michelin': 20000, 'micro contrôle spectra physics - mks': 625,
    'microstore': 150, 'midas': 625, 'midi auto chartres': 150, 'midi caoutchouc': 150, 'midi piles services': 30,
    'migaud': 150, 'migros france': 625, 'migso-pcubed': 3000, 'mikit': 625, 'million victories': 30,
    'miléade': 3000, 'minco': 150, 'mini - gueudet 1880': 3000, 'minimax france sas': 150, 'miramar la cigale hôtel thalasso & spa 5*': 150,
    'mirion technologies france': 625, 'missenard quint b.': 625, 'missions intérim': 30, 'mister minit': 625, 'mistral ai': 625,
    'miti': 150, 'mitsubishi electric france': 625, 'mix buffet': 3000, 'mix buffet traiteur': 30, 'mixscience': 625,
    'mma assurances – groupe covéa': 7500, 'mncap': 150, 'mnt mutuelle nationale territoriale': 3000, 'mo&jo': 30, 'mobalpa': 3000,
    'mobiapps': 150, 'mobilize financial services': 3000, 'molard maintenance': 30, 'mon atout energie 29': 30, 'mon logis': 150,
    'monabanq': 625, 'monaco | avangarde cyber': 625, 'monapp – restopro.': 30, 'monceau assurances': 625, 'mondelez international': 20000,
    'mondial pare-brise': 3000, 'mondial relay by inpost': 3000, 'monext': 625, 'monkey place': 150, 'monoprix - magasins': 20000,
    'monoprix - siège': 20000, 'monspecialisteauto.com': 30, 'montana siège': 150, 'monteiro': 625, 'monts & terroirs': 625,
    'monts jura autocars': 625, 'moongy': 7500, 'moongy digital lab': 150, 'morgan philips specialist': 625, 'mosica': 150,
    'motin freres': 150, 'motul': 625, "moulin d'elise": 150, 'moulin rouge': 625, 'moulins soufflet': 625,
    'mp ascenseurs': 150, 'mph1865': 625, 'mpo fenêtres': 150, 'mpo international': 625, 'mr bricolage': 7500,
    'mr.bricolage': 20000, 'mr.bricolage relais': 30, 'mrc constructions': 30, 'mrod': 30, 'mrs groupe': 625,
    'ms bois': 625, 'msa alpes du nord': 625, 'msa armorique': 625, 'msa loire atlantique - vendée': 625, 'msa maine et loire': 625,
    'msx international': 625, 'mtechbuild': 150, 'mulhouse alsace agglomération': 3000, 'multi-chauffage': 30, 'murano': 30,
    'murex': 3000, 'mustiere automobiles': 30, 'muta santé': 150, 'mutex - groupe vyv': 625, 'mutual logistics': 625,
    'mutuelle interiale': 625, 'mutuelle mgc': 150, 'mutuelle saint christophe': 625, 'mutuelle tutélaire': 150, 'mutuelles du soleil - assurances': 150,
    'mutuelles du soleil - etablissements médico-sociaux': 150, 'mvg industries': 625, 'my pie': 150, 'myconnectedcompany': 150, 'mykids!': 150,
    'mylab': 150, 'myorigines': 150, 'mypos': 625, 'myrium': 3000, 'mytraffic': 150,
    'myttra': 150, 'myunisoft': 150, 'mécamontage': 30, 'mécanojob': 30, 'médipôle hôpital mutualiste': 3000,
    'médor & compagnie': 150, 'métiga': 150, 'mômji': 625, "n'joy": 30, 'n4brands': 150,
    'nacarat': 625, 'nantes métropole': 7500, 'nantes métropole aménagement': 30, 'naos': 3000, 'naskeo environnement': 30,
    'national calsat': 625, 'natran': 3000, 'natup': 3000, 'natural le coultre': 30, 'naturalia france': 3000,
    'nature & découvertes': 3000, 'naturéo': 625, 'nava engineering': 30, 'naval group': 20000, 'naviso': 30,
    'nbtech': 150, 'ned': 150, 'neithwork': 30, 'nemera': 3000, 'neo2': 625,
    'neogest education group': 30, 'neoness': 625, 'neoptim consulting': 150, 'neotoa': 625, 'neptune rh grenoble': 30,
    'nestenn': 3000, 'netcom business services sud': 30, 'netinea': 30, 'netman': 625, 'neubauer groupe': 625,
    'neurones it': 625, "new'r": 30, 'new-e': 30, 'newloc': 625, 'newrest services & supports': 30,
    'nexecur': 30, 'nexteam': 3000, 'nextories': 30, 'nge – nouvelles générations d’entrepreneurs': 20000, 'ngen': 625,
    'ngpa': 625, 'nhood': 3000, 'nibelis': 625, 'nicoll': 625, 'nicomatic': 625,
    'nissan - gueudet 1880': 3000, 'nlj développement': 30, 'nocibé': 3000, 'noemi conseil': 150, 'nomade aventure': 150,
    'nomios': 625, 'norauto': 7500, 'nord btp': 30, 'nord motors': 150, 'nordex france': 625,
    'noremat': 150, 'norgay it & digital services': 625, 'noriap': 625, 'norma': 625, 'normandise petfood': 625,
    'nos hôtels': 150, 'nounou adom': 625, 'nouveaux docks': 30, 'nouvelle clinique bordeaux tondu': 150, 'nouvelles destinations': 30,
    'nouvergies': 30, 'nova': 625, 'novacarb (du groupe humens)': 625, 'novaconseil': 30, 'novae': 150,
    'novaffi': 625, 'novalyo': 30, 'novatech technologies': 150, 'novatrans': 150, 'novebat': 150,
    'novelia': 625, 'noveo': 30, 'noveo group': 625, 'novonesis': 625, 'novotel carquefou': 150,
    'noz': 7500, 'nrj global régions': 625, 'nrj group': 3000, 'nsn industrie': 150, 'ntn europe': 3000,
    'numans': 150, 'numbr': 625, 'numih france': 3000, 'nutribio': 625, 'nutrivendée': 30,
    'nutri’babig': 625, 'nxo experts': 3000, 'néosoft': 3000, "o'logistique": 30, 'o2': 20000,
    'o2 toit': 150, 'oberthur fiduciaire': 625, 'objectware': 625, 'ocea smart building': 625, 'ocsi group': 625,
    'ocy technologies': 150, 'océane consulting': 625, 'océlian': 3000, "oda association oeuvres d'avenir": 625, 'odc': 30,
    'ody-c': 30, 'oet automation': 625, 'office national des forêts': 7500, 'ogmios developpement': 150, 'oissel transports': 150,
    'okaidi': 3000, 'okatim': 30, 'okwind': 150, 'oleon': 150, 'olga': 3000,
    'olys engineering': 150, 'omer-decugis & cie': 150, 'omerin': 3000, 'omexom - lesens actéa': 150, 'omexom isdel energy': 625,
    'omia': 625, 'omnis': 30, 'oméa': 150, 'onela': 3000, 'onepoint': 3000,
    'onera': 3000, 'oneside': 150, 'onet airport services': 20000, 'onet logistique': 625, 'onet technologies': 3000,
    'oney': 3000, "opac de l'oise": 625, 'opac savoie': 625, 'opco 2i': 625, 'opco constructys': 625,
    'opco santé': 625, 'open': 3000, 'open-prod': 150, 'opensourcing': 30, 'oph 05 - hautes alpes': 150,
    'oph de la meuse': 150, 'ophéa': 625, 'oppbtp': 625, 'opstim': 30, 'opteor immotic': 150,
    'opteven': 3000, 'optimhome': 150, 'optineris': 150, 'options solutions': 625, 'optixt': 150,
    'or en cash': 150, 'oralia': 150, 'orange': 20000, 'orange business': 20000, 'orange store': 3000,
    'orano': 20000, 'orc': 30, 'orca accessoires': 150, 'orcab': 150, 'oreca': 150,
    'oreve - ortec group': 30, 'organic alliance (pronatura – vitafrais)': 625, 'orial': 150, 'orinox': 150, 'orion tech': 30,
    'orisha': 3000, 'orisha commerce': 625, 'orona': 625, 'orpi': 7500, 'orsac': 3000,
    'ort toulouse': 150, 'ortec group': 20000, 'orygamy': 150, 'oscaro': 625, 'oteline': 150,
    'otimo': 30, 'otis': 20000, 'otteo': 150, 'ouest boissons': 625, 'ouest france': 3000,
    'ouest isol & ventil': 625, 'ouest pathologie': 150, 'ouest pieces auto logistique': 150, 'ouestotel': 30, 'ouihelp': 625,
    "ouverture's": 625, 'ouvrard': 625, 'ovalis': 150, 'ovelink': 30, 'ovhcloud': 3000,
    'ovive': 150, 'oxb': 625, 'oxymax': 150, 'oxymetal': 625, 'paarly': 30,
    "pack'r": 150, 'pagot savoie': 625, 'pain de belledonne': 150, 'pajot entreprise': 30, 'pam': 30,
    'pangaïa': 30, 'panzani': 625, 'paprec': 20000, 'paradis du fruit': 625, 'paradox museum paris': 30,
    'parc astérix': 3000, 'paris habitat': 3000, 'paris saclay agglomération': 625, 'paris store': 625, 'paritel': 625,
    'parot': 625, 'partedis': 625, 'parthena consultant': 625, 'partners finances': 625, 'parts holding europe': 7500,
    'paul': 625, 'paul boulangerie - brest': 30, 'paysages adeline': 30, 'pb solutions': 30, 'pcer - immosens': 30,
    'peaks': 150, 'pech': 625, 'pellenc st': 625, 'penelope welcome': 3000, 'people&baby': 7500,
    'pepinieres laforet': 150, 'pera paysages': 30, 'perene': 625, "perenne'it": 30, 'perf nut assistance': 625,
    'petit forestier group': 7500, 'petits-fils développement': 625, 'petroineos ineos lavera': 3000, 'peugeot - gueudet 1880': 3000, 'pharma & beauty - saint-chamas | sudcosmetics': 150,
    'pharma & beauty group': 625, 'pharmanimation': 150, 'pharmasys': 150, 'pharmelis': 30, 'philibert transport': 625,
    'phone régie': 3000, 'phosphea': 625, 'phyteo laboratoire': 150, 'picard surgelés': 3000, 'pickup': 625,
    'picnic': 20000, 'picnic technologies': 150, 'pierre gerard': 30, 'pierre hermé paris': 625, 'piman group': 625,
    'pinette emidecau industrie': 150, 'piperno': 625, 'piriou': 625, 'piscines hydrosud': 30, 'pitaya': 30,
    'pixie services france': 150, 'pizzorno environnement': 3000, 'pkf arsilon': 625, 'planète gardiens': 150, 'plateforme les tournesols': 625,
    'platurne': 30, 'plg': 3000, "plur'iel": 30, 'plus que pro': 625, 'pml-promalyon': 30,
    'pms': 30, 'pms médicalisation': 625, 'pmu': 3000, 'pns intérim': 150, 'pny technologies europe': 150,
    'point s group': 30, 'point s réseau': 3000, 'point vert': 625, 'polaris': 30, 'pole de sante du plateau': 625,
    'polyclinique du parc': 625, 'polyclinique du pays de rance': 150, 'polyclinique lyon nord': 625, 'polyclinique saint laurent': 625, 'polyclinique saint-georges': 150,
    'polyexpert france': 3000, 'polytel': 150, 'pomanjou': 150, 'pomona': 20000, 'pomona - délice et création': 3000,
    'pomona - passion froid': 20000, 'pomona - terreazur': 20000, 'pompac': 150, 'ponant': 625, 'ponticelli frères': 7500,
    'pontreau saint lucien – groupe afp': 150, 'poralu groupe': 625, 'portakabin': 150, 'portalp': 625, 'potel et chabot': 625,
    'poudry matériaux': 625, 'poupin': 150, 'pozzo immobilier': 150, 'ppg': 20000, 'pplb': 150,
    'praecisio': 150, 'prb': 625, 'predictis': 150, 'premium foods solutions': 625, 'prenot guinard': 150,
    'presents': 150, "presqu'île – groupe afp": 150, 'presta ain & beaujolais': 150, 'presta silo': 150, 'prestinfo maintenance': 150,
    'pret a manger': 625, 'prevor': 150, 'preysta nord': 150, 'primaprix france': 625, 'primark': 7500,
    'prime engineering': 625, 'primel gastronomie': 625, 'primel gastronomie - plabennec': 30, 'primexis': 625, 'priméale': 7500,
    'prismeo': 625, 'privé s.a.': 150, 'pro armature': 625, 'pro btp': 7500, 'pro distribution': 3000,
    'pro à pro': 3000, 'proadis': 625, 'prodigyus': 30, 'prodomo': 625, 'prodways group': 625,
    'proelan': 150, 'profrais interim': 30, 'progress consulting': 30, 'projecttech engineering': 30, 'projipharm': 30,
    'prolians': 20000, 'prolib': 30, 'promocash': 20000, 'promod': 3000, 'promod magasins': 3000,
    'pronatura': 625, 'propel': 150, 'prosed': 30, 'proselis group': 30, 'prosol': 7500,
    'prospactive': 150, 'proxiad': 3000, 'proxidom services': 625, 'proxiel': 150, 'proximy': 3000,
    'proxiserve': 3000, 'proxiteam': 625, 'proévolution': 30, 'prysm': 150, 'prysmian energie cables et systemes france': 20000,
    'præmia reim': 625, 'préfecture de zone sgami ouest': 625, 'prévoir': 3000, 'pulp immobilier': 150, 'pulse': 30,
    'puma': 625, 'purodor-marosam': 150, 'puybaret': 150, 'pwc france et maghreb': 7500, 'pâtisserie pasquier cerqueux': 625,
    'pâtisserie pasquier etoile': 150, 'pâtisserie pasquier saint-valéry': 625, 'pâtisserie pasquier vron': 625, 'péronnière – groupe afp': 30, 'pôle formation bretagne uimm': 625,
    'qbm marinox': 30, 'qestit': 625, 'qim info': 625, 'qonex': 30, 'quadral': 625,
    'quadral property': 150, 'qualigaz évonia': 150, 'quanteam': 625, 'quantificare': 150, 'queguiner matériaux': 3000,
    'quick': 7500, 'quietalis': 625, 'quincaillerie angles': 625, 'quotatis groupe': 150, 'r2c réalisation chaudronnerie charpente': 30,
    'r2m finances': 625, 'radiall': 3000, 'radiance mutuelle': 150, 'radisson blu grand hôtel & spa malo-les-bains': 625, 'raja france': 625,
    'ramery': 3000, 'randstad digital': 3000, 'ras intérim': 625, 'ratp': 20000, 'ratp cap île-de-france': 3000,
    'ratp dev': 20000, 'ratp habitat': 150, 'razel-bec': 3000, 'rcua': 30, 'rds sas': 30,
    'rds vénissieux': 30, 'rdt ingenieurs': 30, 'reactis services': 150, 'real staffing': 150, 'realisaprint': 150,
    'reals france': 30, 'reca france': 150, 'recherche appartement ou maison': 150, 'recrutement services': 30, 'recrutop': 30,
    'rector lesage': 625, 'recynov': 30, 'reden solar': 150, 'redsup': 30, 'reel': 3000,
    'reel it': 625, 'refectory': 625, 'reflet digital': 150, 'refresco france': 3000, 'regardneuf - courtage en maison individuelle': 30,
    'regardneuf - vente de programmes': 30, 'regardneuf développement foncier': 30, 'regicom': 625, 'region normandie': 3000, 'regional express': 150,
    'reisel': 150, 'rekto': 150, 'relais de chambord': 150, 'relyens': 3000, 'renaissance fusion': 150,
    'renard gillard': 150, 'renaud distribution': 150, 'renault - gueudet 1880': 3000, 'renault group': 20000, 'rennes ville et métropole': 7500,
    'rentokil initial': 3000, 'renée costes viager': 150, 'repam assurances': 150, 'repro-it': 30, 'repsco recrutement': 625,
    'reseau talenz': 3000, 'residences rve': 30, 'resmed': 20000, 'reso (réseaux energies secteur ouest)': 150, 'reso 29': 150,
    'reso 35': 150, 'reso 4972': 150, 'reso 85': 30, 'reso france': 150, 'resoconfort': 150,
    'resonance - groupe firalp': 150, 'resotainer': 150, "restaurant l'embarcadère": 625, 'restaurant le saint laurent': 30, 'restaurant les maritonnes': 30,
    'restonis': 625, 'retailleau': 150, 'reveau menuiserie': 150, 'rexia': 30, 'rey & fils': 150,
    'rfc consulting': 30, 'rgis inventaire': 625, 'rgs': 30, 'rgv groupe': 150, 'rhapsodie gestion': 150,
    'rhapsodies conseil': 150, 'rhd labo': 150, 'rhonatrans': 625, 'riaux escaliers': 625, 'richardson.': 3000,
    'riche & sébastien': 30, 'richel group': 625, 'ridoret betech': 150, 'ridoret distribution': 30, 'ridoret menuiserie': 625,
    'rigolo comme la vie': 625, 'ringover': 625, 'riu paris': 625, 'river café': 150, 'rivière transports': 625,
    'rivp': 3000, 'riwal france': 150, 'rma': 150, 'robatel industries': 150, 'robert half': 20000,
    'robertet': 625, 'roch': 150, 'roch aciers': 30, 'roche': 30, 'roland monterrat': 625,
    'rolesco sas': 150, 'rolot & lemasson': 150, 'rondeau frères': 150, 'roquette': 20000, 'rosalie': 30,
    'rothelec': 150, 'rouenel': 150, 'roussely': 30, 'rouxel beton': 30, 'rouxel citerne': 625,
    'rouxel location': 625, 'rouxel secama': 150, 'rouxel transports': 30, 'roval': 625, 'roxel france': 625,
    'rsm': 3000, 'rt groupe': 150, 'rte': 20000, 'rubafilm': 30, 'rubix france': 3000,
    'rubycat': 30, 'rydge conseil': 3000, "régie de l'eau bordeaux métropole": 625, 'régie des eaux du canal belletrud': 150, 'régie des transports métropolitains': 3000,
    'régie electricité thones': 30, "régie régionale des transports provence-alpes-côte d'azur": 150, 'région bretagne': 3000, 'région pays de la loire': 3000, 'réseau ad': 7500,
    'réseau ducretet - campus lyon': 30, 'réseau ducretet - campus paris': 30, "réseau pil'poele": 30, 'résidence ty noal': 150, 'résilians': 3000,
    'réséda': 30, 's&you': 30, 's.a.l.t société aixoise de location et de transport': 150, 's.i.t.m': 7500, 'sa hlm aximo': 30,
    'sabatier groupe findis': 625, 'sabena technics': 3000, 'sacem': 3000, 'saci technology': 150, 'sacim distribution': 30,
    'sacvl': 150, 'sadaps bardahl corporation s.a.': 30, 'sadec akelys': 625, 'sader réseaux': 150, 'safari technologies': 150,
    'safran': 20000, 'safti': 7500, 'saint clair': 150, 'saint james': 625, 'saint jean industries': 625,
    'saint maclou': 3000, 'saint pierre assurances': 150, 'saint quentin en yvelines agglomération': 625, 'saint yves services': 150, 'saint-gobain': 20000,
    'sainte clothilde – groupe afp': 150, 'saipol': 625, 'salaisons du mâconnais': 150, 'salesfactory': 150, 'salica anconetti': 150,
    'sallard': 30, 'salti': 625, 'samec les sablons smr et ehpad': 150, 'sames': 625, 'samsic emploi': 20000,
    'samsic facility': 20000, 'samsic groupe': 20000, 'samsic médical': 30, 'sanders': 625, 'sanef': 3000,
    'sanisitt': 150, 'sanofi': 20000, 'santévet group': 625, 'sapelli interim': 150, 'sapian': 3000,
    'saprena': 625, 'sarawak gms': 3000, 'sarc (société armoricaine de canalisations)': 625, 'sardel conseil': 150, 'sarenza': 625,
    'saretec group': 3000, 'saric (vestal group)': 150, 'sarl cent flots - sorgues': 150, 'sarl groupe renou': 150, 'sarl quatra france': 625,
    'sas e2v holding': 150, 'sas eric lequertier': 150, 'sas sagir': 150, 'sasi': 150, 'satep': 150,
    'satif': 150, 'satov': 30, 'saur europe': 20000, 'savencia': 20000, 'saverglass': 625,
    'saveurs et vie': 150, 'savoirsplus': 150, 'savoy moulage': 150, 'savpro': 625, 'sc woljung': 30,
    'scaime': 150, 'scalian': 7500, 'scania france': 3000, 'scania production': 625, 'scar': 150,
    'scc': 7500, 'sce': 625, 'scea rené briand': 150, 'sceb - groupe firalp': 30, 'scf': 30,
    'scf-normandie': 30, 'schindler': 3000, 'schmidt': 7500, 'schmidt groupe': 3000, 'schmitt-ney-sfcp': 150,
    'schola nova': 30, 'scic hlm idf habitat': 150, 'sciences po': 3000, 'scje': 150, 'scomet': 30,
    "scop bien l'bonjour !": 30, 'scop espaces verts': 150, 'scp – société du canal de provence': 625, 'screwfix': 150, 'scutum': 625,
    'sdel contrôle commande': 625, 'sdi ventilation': 150, 'sdib': 30, 'sea tpi': 625, 'seal france': 30,
    'seat': 625, 'seb professional': 150, 'sebach': 150, 'secal': 150, 'secob': 625,
    'secomoc': 625, 'sectal': 30, 'securinfor': 625, 'securipro incendie': 150, 'securitas': 20000,
    'securitas technology': 3000, 'sed': 150, 'sedicam': 30, 'seelex': 30, 'seenovate': 150,
    'seequalis': 150, 'sefee': 150, 'sefi': 625, 'segula technologies': 20000, 'sei groupe': 150,
    'seicar': 150, 'seifel': 625, 'seimaf': 150, 'seine-saint-denis habitat': 625, 'sejnera eyssautier expertises': 30,
    'seko logistics france': 150, 'selection med': 30, 'selection ocean': 30, 'selfing': 30, 'semardel': 625,
    'semat': 625, 'semental': 30, 'semeo': 30, 'semios': 150, 'semitan': 3000,
    'semmaris - marché international de rungis': 625, 'semosia': 625, 'senior compagnie recrutement': 3000, 'sensace carrière': 30, 'sensace temporaire': 30,
    'sepamat': 625, 'sepro group': 625, 'seqens': 3000, 'serenest entreprise': 625, 'serenest siege': 625,
    'seres technologies': 150, 'seretram': 150, 'serfim t.i.c.': 150, 'sergic': 3000, 'seris security': 7500,
    'serma ingénierie': 625, 'sermes': 625, 'serpe': 625, 'serpol': 150, 'serpollet': 625,
    'serpollet centre-est': 150, 'serpollet idf': 150, 'serpollet savoie-mont-blanc': 150, 'serpollet sud-est': 30, 'serrurerie luçonnaise': 30,
    'servair': 7500, 'servanin sas': 150, 'serviand': 150, 'servier': 20000, 'servimo': 30,
    'servimo shbir / abs': 30, 'set environnement': 150, 'setec kasadenn': 30, 'setia': 30, 'setra': 625,
    'seven group': 30, 'seyos': 30, 'sferis': 3000, 'sfg services': 150, 'sfhe': 150,
    'sfr': 7500, 'sfr business région ouest': 30, 'sgd pharma': 3000, 'sgs france': 3000, 'shift consulting': 150,
    'shiro games': 150, 'shiva': 3000, 'shopopop': 150, 'shurgard': 150, 'siaap': 3000,
    'siba': 30, 'sibylone': 150, 'sicaf': 150, 'sicame': 3000, 'sicame group': 625,
    'sicap sa': 150, 'sicarev coop': 150, 'sick': 150, 'sicloé': 150, 'sidas': 150,
    'side by randstad': 150, 'sider': 625, 'siehr': 625, 'siemens france': 7500, 'siemens healthineers': 625,
    'sig - service innovation group': 625, 'sig france': 3000, 'sigh': 625, 'sigma': 30, 'siliceo': 150,
    'silkhom': 150, 'sill': 150, 'sill dairy international': 150, 'sim agences d’emploi – région centre': 30, 'simago': 3000,
    'simphonis': 150, 'simplifia': 150, 'sinclair ressources': 150, 'sintegra': 150, 'sintel': 30,
    'sirf': 625, 'sis': 625, 'sit&a conseil': 30, 'sites': 625, 'sitour': 150,
    'sivemat': 150, 'sixense engineering': 150, 'size up consulting': 150, 'skills banque et assurance': 30, 'skills grenoble': 150,
    'skills lyon': 150, 'skills marseille': 150, 'skills massy': 150, 'skills montigny': 150, 'skills nantes': 150,
    'skills nice': 150, 'skills orléans': 150, 'skills paris': 150, 'skills rennes': 150, 'skills rouen': 150,
    'skills vendée poitou-charentes': 150, 'skoda': 150, 'sm3 claas': 625, 'smabtp': 3000, 'smac': 3000,
    'smart tale': 30, 'smf services': 150, 'smmi': 30, 'smovengo': 625, 'smri': 625,
    'snaam': 625, 'sncf connect & tech': 3000, 'sncf voyageurs': 20000, 'sne chiarella': 150, 'snee': 625,
    'snef': 20000, 'snef power services': 3000, 'snexi': 30, 'snf': 3000, 'snipes': 3000,
    'snow group': 625, 'sns security': 150, 'so.bio, bio c’ bon, le grand panier bio': 625, 'sobaten': 30, 'sobeca - groupe firalp': 3000,
    'soc breton canalisa eau assain audo cie (sbcea)': 30, 'socaps consulting': 150, "socass - société d'assistance de service et de support": 150, 'social inter': 150, 'société axelis tertre': 625,
    "société dauphinoise pour l'habitat": 625, 'société de travaux du centre est': 625, 'société française de garantie': 150, 'socobois': 150, "socoo'c": 3000,
    'socotec': 20000, 'socovo': 30, 'sodebo': 3000, 'sodecal': 150, 'sodetrav': 20000,
    'sodexo': 20000, 'sodiaal': 7500, 'sodiaal professionnel': 30, 'sodiaal union': 30, 'sofia holding': 625,
    'sofimat': 150, 'sofinther': 625, 'sofipel': 150, 'sofitex': 3000, 'sofragrain': 30,
    'sofrat': 150, 'sofratel': 30, 'sofreba': 150, 'sofripa': 150, 'sofultrap': 150,
    'sogea environnement': 3000, 'sogedex accessories': 30, 'sogedo': 625, 'sogema': 150, 'sogescot': 30,
    'sogestran group': 3000, 'sogestran shipping': 3000, 'sogeti': 20000, 'sogetrel': 3000, 'solano intérim': 150,
    'solargie': 30, 'solimut mutuelle de france': 625, 'solipac - hrc environnement': 150, 'sollers consulting': 30, 'solocal group': 3000,
    'solutec': 3000, 'solutions 30': 7500, 'solutions compétences': 150, 'soluxan': 30, 'soma': 150,
    'someca': 3000, 'somelec - groupe firalp': 150, 'sommereisen': 30, 'sonepar france': 7500, 'sonoco - chatillon': 7500,
    'sonoco - nantes': 625, 'sonoco concarneau': 20000, 'sonoco france': 20000, 'sonova': 20000, 'sonovision - ortec group': 3000,
    'sophia engineering': 625, 'sopra steria': 20000, 'soprema entreprises': 3000, 'soprema france': 3000, 'soredi': 30,
    'sorelec': 150, 'sorelum': 30, 'sorofi': 625, 'sos mad': 30, 'sos oxygène': 3000,
    'sosan': 625, 'sotel groupe': 625, 'soufflet agriculture': 3000, 'soufflet malt': 625, 'source – groupe afp': 625,
    'sources alma': 625, 'sovec entreprises': 625, 'sovetours': 625, 'sowink': 30, 'spac': 3000,
    'spartoo': 625, 'spash': 30, 'specilor sas': 150, 'speedway': 150, 'speedy': 3000,
    'spg': 150, 'sphere france': 3000, 'spherio': 150, 'spi group': 625, 'spie batignolles': 7500,
    'spie building solutions': 3000, 'spie citynetworks': 3000, 'spie facilities': 3000, 'spie france': 20000, 'spie global services energy': 3000,
    'spie ics': 3000, 'spie industrie': 3000, 'spie nucléaire': 3000, 'spie operations': 20000, 'spineart': 30,
    'spirica': 150, 'sponsor rh': 30, 'sport 2000 - s2k73': 150, 'sportingsols': 30, 'sppf': 150,
    'spph': 625, 'sprd': 30, 'squad': 625, 'square habitat': 625, 'square habitat aquitaine': 150,
    'square habitat nord de france': 625, 'square lodge': 30, 'square management': 625, 'squiban group': 625, 'sra': 625,
    'ssi service': 625, 'st michel biscuits': 3000, 'stacem': 625, 'staci': 3000, 'stade rennais football club': 150,
    'staff décor': 150, 'staffmatch': 625, 'staffmatch france permanent': 625, 'stallergenes greer': 625, 'standard textile': 150,
    'standardaero france': 150, 'starbucks': 150, 'starbucks france': 3000, 'starclay': 30, 'starmat': 7500,
    'start people, rejoignez-nous': 625, 'startrucks': 150, 'stb siege': 30, 'ste grand sud': 150, 'ste infra-spe': 150,
    'steep plastique': 150, 'stef': 20000, 'stellantis &you': 3000, 'stelliant': 3000, 'stelogy': 625,
    'stem groupe': 7500, 'step up': 150, 'stephid': 625, 'sterem france': 30, 'stg': 3000,
    'stgs sas': 625, 'stid': 150, 'still': 625, 'sto': 625, 'stockmeier france': 625,
    'stokomani': 3000, 'stork groupe': 30, 'stormshield': 625, 'stradal': 625, 'strapharm': 30,
    'stratus packaging': 625, 'streem': 30, 'sts': 150, 'sts group': 3000, 'sttraten': 30,
    'studec': 150, 'studiel': 625, 'studio recrutement': 30, 'studiosanté': 30, 'study rail': 30,
    'sturno sas': 150, 'stych': 625, 'styrel': 30, 'subrenat': 150, 'sucralliance': 625,
    'sud métal provence': 30, 'sud ouest caoutchouc': 150, 'sud-ouest aliment': 625, 'suez': 20000, 'sully group': 625,
    'suma': 625, 'sumup': 30, 'sunclear': 625, 'sundis': 150, 'sunglass hut france': 625,
    'sunroad equipment': 625, 'sunzil': 150, 'sup de vinci': 150, 'super u - plogonnec': 150, 'supergroup': 625,
    'supermarchés match': 7500, 'supratec': 150, 'suravenir': 625, 'suravenir assurances': 625, 'swisslog healthcare': 150,
    'syd digital care': 150, 'sygma engineering services': 30, 'sygmatel': 625, 'sygnatures': 150, 'symbioz': 150,
    'synanto': 625, 'synapsco': 150, 'synchrone': 3000, 'syncura': 150, 'synergie': 3000,
    'synergie care': 30, 'synergie engineering': 150, 'synergie technologies': 30, 'synetics': 625, 'synext': 30,
    'synfolia': 30, 'synlab': 3000, 'sys télécoms': 30, 'sysco france': 3000, 'systra': 3000,
    'système wolf': 625, 'séché environnement': 7500, "t'rhea": 625, 't-t consulting': 625, 't.t.e.c. - groupe hermitage': 30,
    't2cs': 150, 'takoma': 150, 'talan': 7500, 'talentdigger': 30, 'talents crit': 3000,
    'talents supply': 30, 'talhent': 150, 'talia': 150, 'tanaïs habitat': 30, 'tang frères': 625,
    'tanguy matériaux distribution': 625, 'tap': 625, "tape à l'oeil": 625, 'tara jarmon': 150, 'tata steel maubeuge': 625,
    'taylor made recrutement': 30, 'tbr': 150, 'tbs siège': 150, 'td synnex': 625, 'tea alsace': 7500,
    'tea la norville': 30, 'team active': 625, 'team it': 150, 'team ouest distralis': 625, 'team reseaux': 150,
    'team y': 30, 'tech enr': 30, 'techfirm consulting': 150, 'techmo hygiene': 625, 'techna': 150,
    'technal': 150, 'technicatome': 3000, 'technichauffe': 150, 'technimodern automation': 30, 'technitoit': 625,
    'technord': 625, 'techteam': 30, 'tecnizy-gcat group': 150, 'tecxell intérim': 30, 'telelec réseaux': 150,
    'telenco': 625, 'tellus': 625, 'telstar': 150, 'temiq': 30, 'temporis experts et cadres': 625,
    'temporis interim': 625, 'tempur sealy france': 150, 'tendriade': 625, 'tenexa group': 625, 'teodis': 625,
    'tepasso': 150, 'ter': 625, "ter'informatique": 30, 'teract': 7500, 'teremat': 150,
    'tereos': 20000, 'terideal': 3000, 'ternois fermetures': 625, 'terre occitane': 30, 'terrena': 20000,
    "terres de l'ouest": 625, 'terres des templiers': 150, 'terres lyonnaises': 150, 'terresis': 625, 'terrial': 150,
    'territoria  prévoyance': 150, 'terélian': 625, 'tes engineering': 150, 'tessi groupe': 20000, 'testo industrial services': 150,
    'tetris assurance': 150, 'tevah systemes': 150, 'texdecor group': 625, 'tgs france': 3000, 'th trucks daf nissan': 150,
    'thelem assurances - reseau': 625, 'thelesys': 30, 'therm-sanit equipement hydraulique': 150, 'theseis': 625, 'thiebaut': 30,
    'thiriez literie': 150, 'thélem assurances': 625, 'théodore maison de peinture': 625, 'théolaur peintures': 150, 'thévenin sa': 625,
    'tibbloc': 150, 'tiime': 150, 'tillou crèche': 150, 'tilyo': 30, 'timac agro france': 625,
    'timac agro international': 3000, 'timcod': 150, 'timet savoie': 150, 'timtargett': 30, 'tipiak': 150,
    'tipmat': 150, 'tisseo services': 625, 'tisserin habitat': 30, 'tisserin immobilier': 625, 'tisserin maison individuelle': 150,
    'tisserin promotion': 30, 'tisséo voyageurs': 3000, 'tk elevator france': 3000, 'tld europe': 625, 'tmc béjenne': 30,
    'tmc france sud-ouest': 30, 'tmf operating': 625, 'tmfop': 30, 'tohtem': 30, 'toolog': 150,
    'top services': 150, 'topigs norsvin': 625, 'topsolid': 625, 'toray carbon fibers europe': 625, 'torow': 150,
    'totalenergies proxi sud-est': 625, 'toujas & coll': 150, 'tout cérébrolésé assistance': 150, 'toyota - gueudet 1880': 3000, 'toyota material handling manufacturing france': 625,
    'tpb (travaux publics du blavet)': 30, 'tpc ouest': 150, 'tradival': 3000, 'trans europ express': 150, 'transcausse': 150,
    'transdev savoie': 20000, 'transgourmet': 3000, 'translocauto': 150, 'transmanut': 30, 'transplaneze': 150,
    'transport ltr vialon': 625, 'transports avril': 150, 'transports bertin': 150, 'transports brodu': 150, 'transports chalavan et duc': 3000,
    'transports clot sarl': 150, "transports de l'ain": 625, 'transports derocq': 150, 'transports faillu tony': 30, 'transports feuillet': 150,
    'transports france alliance 44': 150, 'transports groussard': 30, 'transports martin': 30, 'transports prevost': 150, 'transports rouxel': 30,
    'traou mad.': 150, 'trecobat': 625, 'tredelec': 150, 'trenois decamps': 625, 'tresallet': 30,
    'trescal': 3000, 'tressol chabrier': 3000, 'triangle appro': 150, 'triangle intérim': 3000, 'triangle énergie': 150,
    'triballat': 3000, 'tribay': 30, 'trigo': 625, 'trillium flow technologies': 625, 'trimet': 625,
    'triomphe sécurité': 3000, 'trirx': 150, 'tronico': 625, 'truffaut': 3000, 'trusk france': 150,
    'trustteam france': 625, 'trèfle ingénierie': 150, 'trèfle ita': 30, 'trèfle solution': 30, 'tse energy': 150,
    'tuanis conseil': 30, 'tunzini maintenance nucléaire': 150, 'turquand': 150, 'tve logistique': 625, 'tyls conseil': 625,
    'työ': 30, 'téréva': 3000, 'téréva adv': 3000, 'u-need sas': 150, 'uaf life patrimoine': 150,
    'ubbink france': 150, 'udaf 93': 150, 'udaf de l’essonne': 150, 'udaf94': 150, 'udife': 150,
    'udife assurances': 3000, 'uff': 625, 'ugap': 3000, 'ugitech de swiss steel group': 3000, 'ullis': 30,
    'ulule': 150, 'umake': 150, 'umane': 3000, 'umaneïs rh': 30, 'umg groupe vyv': 625,
    'umr groupe vyv': 150, 'unac': 150, 'unapei alpes provence': 3000, 'undiz': 625, 'une pièce en plus': 150,
    'une villa et des vignes': 30, 'unibio': 30, 'unicil': 625, 'unik emploi': 30, 'unikalo': 3000,
    'unilabs': 3000, 'union invivo': 3000, 'union materiaux': 625, 'union nouvelle leman': 625, 'union nouvelle seynod': 30,
    'union plastic': 150, 'uniqlo': 3000, 'united solutions': 30, 'univar solutions': 625, 'univers retail': 150,
    'unixo': 30, 'unyc': 150, 'up sell': 150, 'upl': 20000, 'uptoo': 150,
    'ussap': 3000, 'utigroup': 625, 'utwin': 150, 'uuds': 625, "uxello - l'expertise protection incendie chez vinci energies en france": 625,
    'v33': 625, 'vacancéole': 625, 'vacoa': 30, 'vaduo consulting': 30, 'vai brassac': 30,
    'vai brioude': 30, 'vai cournon': 30, 'vai issoire': 30, 'vai saint flour': 30, 'vai thiers': 30,
    "val d'eurre": 150, 'valdepharm': 625, 'valentin traiteur': 625, 'valeo': 20000, 'vallier energies': 30,
    'valobat': 150, 'valotrans': 30, 'valtec france': 150, 'vandemoortele': 7500, 'var habitat': 625,
    'vast pro': 150, 'vaudaux': 150, 'vcp - telegramme': 625, 'vcsp batiment nord est et ansc': 150, 'vcsp route france - delegation sud ouest': 20000,
    'vdcom': 150, 'vdl conseil': 625, 'vef industrie arc alpin': 150, 'vef industrie loire rhône': 30, 'vef industrie rhône alpes maintenance et logistique': 30,
    'vef tertiaire périmètre occitanie': 150, 'vef tertiaire périmètre paca': 30, 'vef tertiaire périmètre rhône / ain': 20000, 'vegecroc': 150, "vendeurs d'excellence": 30,
    'vendez seul immo': 30, 'vendezvotrevoiture.fr': 625, 'vendée fluides energies': 150, 'vendée habitat': 625, 'veng hour': 150,
    'ventimeca groupe': 150, 'veolia': 20000, 'veolia agriculture france': 625, 'veolia assainissement et maintenance': 7500, 'veolia eau': 20000,
    'veolia energie & décarbonation': 625, 'veolia energie performance': 3000, 'veolia environnement': 20000, 'veolia hazardous waste europe': 3000, 'veolia ingénierie et conseil': 150,
    'veolia nuclear solutions': 30, 'veolia recyclage et valorisation des déchets': 3000, 'verdi bureau d’etudes ingenierie et conseil': 625, 'veritech': 30, 'verlingue': 3000,
    'vernet behringer': 150, 'verspieren': 3000, "vertical'art": 150, 'vertuo santé': 625, 'vertys': 30,
    'veryswing': 30, 'vestas france': 625, 'vetagri': 150, 'veternity': 625, 'vetoquinol': 3000,
    'veyres-perie': 150, 'vezie réseaux': 150, 'vialis': 625, 'viamedis': 150, 'viaposte': 3000,
    'viatris': 3000, 'vidi': 3000, 'vigny depierre assurance': 150, 'vilebrequin france': 150, 'villa beausoleil': 625,
    'villa castellane': 30, 'villa saint ange': 30, 'villadim solutions habitat': 150, 'villages clubs du soleil': 625, "ville d'angers": 7500,
    "ville d'annecy": 3000, 'ville de cavaillon': 625, 'ville de chevreuse': 150, 'ville de lyon': 7500, 'ville de mulhouse': 3000,
    'ville de sèvres': 625, 'ville du touquet-paris-plage': 625, 'vilmorin jardin - groupe limagrain': 150, 'vilmorin-mikado - groupe limagrain': 150, 'vim': 625,
    'vinci autoroutes': 7500, 'vinci construction - cardem': 625, 'vinci construction - délégation batiment nord-ouest': 625, 'vinci construction - signature': 3000, 'vinci construction division route france délégation idfn': 20000,
    'vinci construction france - direction opérationnelle ouvrages fonctionnels neufs': 625, 'vinci construction france délégation génie civil ouest': 20000, 'vinci energies activité nucléaire': 3000, 'vinci energies france industrie automation': 30, 'vinci energies france industrie auvergne': 30,
    'vinci energies france industrie nord et est': 30, 'vinci energies france industrie normandie idf': 30, 'vinci energies france industrie ouest-atlantique & pacifique': 20000, 'vinci energies france infras idf nord est': 150, 'vinci energies france infras méditerranée centre-est': 30,
    'vinci energies france infras sud ouest antilles guyane': 30, 'vinci energies france tertiaire centre est sud': 20000, 'vinci energies france tertiaire idf': 30, 'vinci energies france tertiaire nord est': 150, 'vinci energies france tertiaire périmètre arc alpin': 30,
    "vinci energies infrastructures provence alpes côte d'azur": 30, 'vinci energies nucleaire - cegelec nucléaire sud est': 20000, 'vinci energies nucléaire - cegelec cem': 625, 'vinci facilities bretagne': 150, 'vinci facilities centre': 150,
    'vinci facilities copernic idf ouest': 150, 'vinci facilities copernic ouest': 150, 'vinci facilities information technologies services': 625, 'vinci facilities loire ocean': 30, 'vinci immobilier': 3000,
    'vinci sa': 20000, 'vink france': 150, 'viola - groupe firalp': 150, 'viparis': 625, 'viqi': 150,
    'virbac': 7500, 'viria': 150, 'virtuos france': 625, 'vision interim': 30, 'vital concept': 625,
    'vitalliance': 7500, 'vitalliance siège': 7500, 'vitalrest': 3000, 'vitibot': 150, 'vivaservices': 3000,
    'viverio': 150, 'viveris.': 625, 'vivest': 625, 'vivialys': 625, 'vivien paille': 625,
    'vivisol france': 625, 'vivre adom': 625, 'vivre en bois': 625, 'vlok': 150, 'voies navigables de france': 3000,
    'volfoni': 150, 'volkswagen': 625, 'volkswagen - gueudet 1880': 3000, 'volkswagen groupe france academy': 150, 'volkswagen véhicules utilitaires': 625,
    'voltania': 30, 'volvo group': 20000, 'vorwerk france': 7500, 'vossloh switch systems': 3000, 'vous faciliter l’it - vflit': 150,
    'vousfinancer': 625, 'voyages cordier': 150, 'voyages quérard': 150, 'voyages rigaudeau': 30, 'voyelle.fr': 30,
    'vpsitex': 150, 'vsn': 30, 'vst': 625, 'vulcain engineering group': 7500, 'vusion': 3000,
    'vygon': 3000, 'vyv 3': 20000, 'vyv 3 bourgogne': 20000, 'vyv 3 bourgogne - ecouter voir': 20000, 'vyv 3 bourgogne - vyv dentaire': 20000,
    'vyv 3 bretagne': 3000, 'vyv 3 bretagne - ecouter voir': 20000, 'vyv 3 bretagne - vyv dentaire': 20000, 'vyv 3 centre-val de loire': 3000, 'vyv 3 centre-val de loire - ecouter voir': 3000,
    'vyv 3 centre-val de loire - vyv dentaire': 3000, 'vyv 3 ile de france': 20000, 'vyv 3 ile de france - ecouter voir': 20000, 'vyv 3 ile de france - vyv dentaire': 20000, 'vyv 3 pays de la loire': 3000,
    'vyv 3 pays de la loire – vyv dentaire': 20000, 'vyv 3 sud-est - vyv dentaire': 3000, 'vyv équipement médical': 625, 'vyv3 - sas optique et audition': 20000, 'vyv3 – sas optique et audition ecouter voir': 20000,
    'vêpres': 150, 'walon': 3000, 'walter learning': 150, 'wasabi corner': 625, 'waykom': 30,
    'wc loc': 625, 'we fix': 625, 'we invest real estate france': 30, 'we+': 625, 'weeneo consulting': 150,
    'weishaupt': 625, 'welcoop solution produits': 150, 'weldom s.a': 3000, "well'd": 150, 'wellington': 150,
    'westotel le pouliguen': 150, 'wevii': 150, 'whiskies du monde': 30, 'wicona': 625, 'wienerberger': 20000,
    'willy naessens': 150, "win'up": 30, 'winamax': 625, 'winsearch': 150, 'winside technology': 150,
    'winterhalter france': 150, 'wise rh': 30, 'wiziou': 30, 'wom': 30, 'wonderbox': 150,
    'work & you': 30, 'wtw': 20000, 'wurth elektronik france': 150, 'würth france': 3000, 'xefi': 3000,
    'xelians': 625, 'xenassur': 30, 'xpfibre': 625, 'xpo logistics': 7500, 'xs groupe': 30,
    'yalink': 30, 'yamaha motor': 150, 'yanmar construction equipment europe sas': 625, 'yantec': 30, 'yellow korner': 150,
    'yes !': 150, 'yesss electrique': 3000, 'ymca services occitanie': 625, 'yoplait': 3000, 'yumens': 150,
    'yves rocher': 20000, 'yxia': 150, 'zach system': 150, 'zapa': 625, 'zenith investment solutions': 30,
    'zenith it consulting': 30, 'zooparc de beauval': 625, 'établissements cancé': 625,
}

def size_bucket(n):
    """Convertit un nb_employees en tranche lisible."""
    if not n:
        return None
    try:
        n = int(n)
    except (ValueError, TypeError):
        return None
    if n <= 10:    return '≤10'
    if n <= 50:    return '11–50'
    if n <= 200:   return '51–200'
    if n <= 1000:  return '201–1k'
    if n <= 5000:  return '1k–5k'
    return '5k+'

def _cache_size(company, nb_employees):
    """Enregistre la taille dans le cache si valide."""
    if not company or not nb_employees:
        return
    try:
        n = int(nb_employees)
        if n > 0:
            _company_size_cache[company.lower().strip()] = n
    except (ValueError, TypeError):
        pass

# Codes INSEE tranche_effectif_salarie → nombre représentatif
_INSEE_TRANCHE = {
    '00': 0,  '01': 1,  '02': 4,  '03': 7,
    '11': 14, '12': 34, '21': 74, '22': 149,
    '31': 224,'32': 374,'41': 749,'42': 1499,
    '51': 3499,'52': 7499,'53': 14999,'54': 30000,
}
GOUV_API = 'https://recherche-entreprises.api.gouv.fr/search'

def _name_similarity(a, b):
    """Simple token overlap — retourne True si les noms se ressemblent assez."""
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return True
    # Remove common legal suffixes
    for sfx in (' sas',' sarl',' sa',' srl',' group',' groupe',' france',' holding'):
        a = a.replace(sfx, '')
        b = b.replace(sfx, '')
    a, b = a.strip(), b.strip()
    if a == b or a in b or b in a:
        return True
    # Token overlap ≥ 50%
    ta = set(re.split(r'\W+', a)) - {'', 'le', 'la', 'les', 'de', 'du', 'des', 'et'}
    tb = set(re.split(r'\W+', b)) - {'', 'le', 'la', 'les', 'de', 'du', 'des', 'et'}
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / max(len(ta), len(tb))
    return overlap >= 0.6

def _pappers_lookup(company_name):
    """Interroge l'API gouvernementale (sans clé) — fallback uniquement."""
    try:
        url = GOUV_API + '?' + urllib.parse.urlencode({
            'q': company_name, 'per_page': 3,
        })
        req = urllib.request.Request(url, headers={'User-Agent': 'JobRadar/1.0'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=8)
        data = json.loads(resp.read())
        for r in data.get('results', []):
            api_name = r.get('nom_complet') or r.get('nom_raison_sociale') or ''
            if not _name_similarity(company_name, api_name):
                continue
            code = r.get('tranche_effectif_salarie') or ''
            n = _INSEE_TRANCHE.get(code)
            if n and n > 0:
                return n
    except Exception:
        pass
    return None

def enrich_company_size(jobs):
    """Applique le cache de taille à tous les jobs, avec fallback API gouv."""
    # Seed avec les valeurs connues (si pas déjà dans le cache)
    for name, n in KNOWN_COMPANY_SIZES.items():
        _company_size_cache.setdefault(name, n)

    # Passe 1 : cache local (HW + WTTJ/SF + hardcoded)
    missing = []
    covered = 0
    for j in jobs:
        if j.get('company_size'):
            covered += 1
            continue
        name = (j.get('company') or '').lower().strip()
        n = _company_size_cache.get(name)
        if n is None:
            for k, v in _company_size_cache.items():
                if k and (k in name or name in k) and len(k) >= 4:
                    n = v
                    break
        if n:
            j['company_size'] = n
            covered += 1
        else:
            j['company_size'] = None
            missing.append(j)

    # Passe 2 : fallback API gouvernementale (une requête par entreprise unique)
    unique_missing = {}
    for j in missing:
        name = (j.get('company') or '').strip()
        if name and name not in unique_missing:
            unique_missing[name] = []
        if name:
            unique_missing[name].append(j)

    api_found = 0
    for company, jlist in unique_missing.items():
        n = _pappers_lookup(company)
        if n:
            _company_size_cache[company.lower().strip()] = n
            for j in jlist:
                j['company_size'] = n
            api_found += 1
            covered += len(jlist)
        time.sleep(0.15)  # gentle rate limit

    print(f'  Taille entreprise : {covered}/{len(jobs)} jobs enrichis '
          f'({api_found} via API gouv, {len(unique_missing)-api_found} inconnus)')

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

    jobs, batch = [], 50

    # ── 1. Sonde initiale : récupère totalCount pour partir de la fin ──────────
    # L'API APEC trie les offres de la plus ancienne (index 0) à la plus récente
    # (index totalCount-1). On calcule le startIndex pour ne prendre que les
    # `max_results` offres les plus récentes.
    def _apec_req(si, rng):
        body = json.dumps({
            'typesConvention': [143684],   # CDI
            'fonctions': [101833],          # Informatique
            'secteursActivite': [],
            'motsCles': '',
            'lieux': [],
            'pagination': {'startIndex': si, 'range': rng},
        }).encode('utf-8')
        req = urllib.request.Request(APEC_SEARCH, data=body, headers=h2, method='POST')
        resp = opener.open(req, timeout=20)
        return _apec_decode(resp)

    try:
        probe = _apec_req(0, 1)
        total = probe.get('totalCount', 0)
    except Exception as e:
        print(f'  APEC sonde erreur: {e}')
        return []

    print(f'  [APEC] totalCount={total}, on part de la fin')
    start = max(0, total - max_results)  # commence aux offres récentes

    while len(jobs) < max_results:
        try:
            data = _apec_req(start, batch)
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

            # Age — format API: "2026-05-19T10:34:58.000+0000"
            date_str = r.get('datePublication', '')
            try:
                # Normalise offset "+0000" → "+00:00" pour fromisoformat
                ds = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', date_str)
                dp = datetime.fromisoformat(ds)
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

            slug    = h.get('slug') or oid
            wo      = org.get('website_organization') or {}
            wo_slug = (wo.get('slug') if isinstance(wo, dict) else None) or org.get('slug') or ''
            link    = f'{SF_BASE}/companies/{wo_slug}/jobs/{slug}' if wo_slug else f'{SF_BASE}/jobs/{slug}'

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

            nb_emp = org.get('nb_employees')
            _cache_size(company, nb_emp)

            jobs.append({
                'id':           1300000 + len(jobs),
                'title':        title,
                'company':      company,
                'link':         link,
                'desc':         '',
                'location':     location,
                'category':     categorize(title, ''),
                'daysAgo':      days_ago,
                'logo':         logo,
                'isESN':        is_esn_company(company),
                'isCabinet':    is_cabinet(company),
                'source':       'sf',
                'company_size': int(nb_emp) if nb_emp else None,
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

# ── Fonds d'investissements (Getro) ──────────────────────────────────────────
#
# Boards Getro : POST https://api.getro.com/api/v2/collections/{network_id}/search/jobs
# Pagination : 20 par page, champ `results.count` = total.
# Ajouter un fonds = 1 ligne dans GETRO_BOARDS.

GETRO_BOARDS = [
    # (display_name, source_id, network_id, base_url)
    ('Daphni',   'daphni',   '3359',  'https://talent.daphni.com'),
    ('Partech',  'partech',  '10421', 'https://portfoliojobs.partechpartners.com'),
]

GETRO_API = 'https://api.getro.com/api/v2/collections/{}/search/jobs'

def fetch_getro(display_name: str, source_id: str, network_id: str, base_url: str) -> list:
    """Generic fetcher for Getro-hosted VC job boards."""
    api_url = GETRO_API.format(network_id)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': base_url,
        'Referer': base_url + '/jobs',
    }

    jobs, seen, page, total = [], set(), 1, None

    while True:
        body = json.dumps({
            'hitsPerPage': 20,
            'page': page,
            'filters': {'searchable_locations': ['France']},
            'query': '',
        }).encode()
        req = urllib.request.Request(api_url, data=body, method='POST', headers=headers)
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=15)
            data  = json.loads(resp.read())
        except Exception as e:
            print(f'  [{display_name}] page {page} erreur: {e}')
            break

        results = data.get('results', {})
        hits    = results.get('jobs', [])
        if total is None:
            total = results.get('count', 0)

        if not hits:
            break

        for j in hits:
            jid = str(j.get('id') or j.get('slug', ''))
            if not jid or jid in seen:
                continue
            seen.add(jid)

            title   = (j.get('title') or '').strip()
            org     = j.get('organization') or {}
            company = (org.get('name') or '').strip()
            if not title or not company:
                continue

            # URL : priorité au lien source direct, sinon page Getro
            link = j.get('url') or f'{base_url}/jobs/{j.get("slug","")}'

            # Location
            locs = j.get('locations') or j.get('searchable_locations') or []
            wmode = j.get('work_mode') or ''
            if wmode in ('remote', 'fully_remote'):
                location = 'Remote'
            elif locs:
                # Keep shortest (most specific) location string
                loc_raw = min(locs, key=len)
                # Normalise: "Paris, France" → "Paris"
                loc_raw = loc_raw.split(',')[0].strip()
                location = ms_normalize_location(loc_raw, '')
            else:
                location = 'France'

            # Age (Unix timestamp)
            created = j.get('created_at') or 0
            try:
                age = max(0, (datetime.now(timezone.utc) -
                              datetime.fromtimestamp(created, tz=timezone.utc)).days)
            except Exception:
                age = 99

            # Logo
            logo = org.get('logo_url') or org.get('logoUrl') or None

            jobs.append({
                'id':           900000 + len(jobs),
                'title':        title,
                'company':      company,
                'link':         link,
                'desc':         '',
                'location':     location,
                'category':     categorize(title, ''),
                'daysAgo':      age,
                'logo':         logo,
                'company_size': None,
                'isESN':        is_esn_company(company),
                'isCabinet':    is_cabinet(company),
                'source':       source_id,
            })

        print(f'  [{display_name}] page {page}/{(total//20)+1} → {len(hits)} offres')

        if len(jobs) >= total or not hits:
            break
        page += 1
        time.sleep(0.5)

    print(f'  [{display_name}] total: {len(jobs)} offres')
    return jobs

# ── Fonds d'investissements (WelcomeKit) ─────────────────────────────────────
#
# Chaque fonds hébergé sur WelcomeKit utilise le même Algolia
# (APP_ID = CSEKHVMS53, index = wk_cms_jobs_production_careers) avec une clé
# restreinte récupérée dynamiquement depuis la page d'accueil du job-board.
# Ajouter un nouveau fonds = 1 ligne dans FUND_BOARDS ci-dessous.

FUND_BOARDS = [
    # (display_name,  source_id,  welcomekit_base_url)
    ('Elaia',         'elaia',    'https://elaia.welcomekit.co'),
]

WK_APP_ID = 'CSEKHVMS53'
WK_INDEX  = 'wk_cms_jobs_production_careers'

def _wk_parse_size(size_fr: str) -> int | None:
    """Parse WelcomeKit org size label (French) → representative int."""
    if not size_fr:
        return None
    s = size_fr.lower()
    m = re.search(r'entre\s+(\d+)\s+et\s+(\d+)', s)
    if m:
        return (int(m.group(1)) + int(m.group(2))) // 2
    m2 = re.search(r'moins\s+de\s+(\d+)', s)
    if m2:
        return int(m2.group(1)) // 2
    m3 = re.search(r'plus\s+de\s+(\d+)', s)
    if m3:
        return int(m3.group(1)) * 2
    return None

def fetch_welcomekit(display_name: str, source_id: str, base_url: str) -> list:
    """Generic fetcher for any WelcomeKit-hosted job board."""
    # 1. Récupère la clé Algolia depuis la page d'accueil
    try:
        page_req = urllib.request.Request(base_url + '/', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        page_resp = urllib.request.urlopen(page_req, context=ctx, timeout=15)
        page_html = page_resp.read().decode('utf-8', errors='replace')
        m = re.search(r'id="algolia_api_key" value="([^"]+)"', page_html)
        if not m:
            print(f'  [{display_name}] clé Algolia introuvable')
            return []
        api_key_b64 = m.group(1)
    except Exception as e:
        print(f'  [{display_name}] erreur chargement page: {e}')
        return []

    # 2. Requête Algolia (CDI uniquement, toutes pages)
    qs = urllib.parse.urlencode({
        'x-algolia-agent': 'Algolia for JavaScript (3.35.0); Browser (lite)',
        'x-algolia-application-id': WK_APP_ID,
        'x-algolia-api-key': api_key_b64,
    })
    algolia_url = f'https://{WK_APP_ID.lower()}-dsn.algolia.net/1/indexes/*/queries?{qs}'

    jobs, seen = [], set()
    page, nb_pages = 0, 1

    while page < nb_pages:
        hit_params = urllib.parse.urlencode({
            'enableABTest': 'false',
            'query': '',
            'page': page,
            'hitsPerPage': 100,
            'facetFilters': '[["contract_type_names.en:Full-Time"]]',
        })
        payload = json.dumps({'requests': [{'indexName': WK_INDEX, 'params': hit_params}]}).encode()
        req = urllib.request.Request(algolia_url, data=payload, method='POST',
                                     headers={'Content-Type': 'application/json'})
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=15)
            result = json.loads(resp.read())['results'][0]
        except Exception as e:
            print(f'  [{display_name}] page {page} erreur: {e}')
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
            link = f'{base_url}/jobs/{slug}'

            # Location
            offices    = h.get('offices') or []
            remote_val = h.get('remote') or ''
            if remote_val in ('remote', 'fulltime'):
                location = 'Remote'
            elif offices:
                location = offices[0].get('city') or offices[0].get('district') or 'France'
            else:
                location = 'France'
            location = ms_normalize_location(location, '')

            # Date
            date_str = h.get('published_at', '')
            try:
                ds = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', date_str)
                dp = datetime.fromisoformat(ds)
                age = max(0, (datetime.now(timezone.utc) - dp).days)
            except Exception:
                age = 99

            # Logo
            logo = None
            logo_obj = org.get('logo') or {}
            thumb = (logo_obj.get('thumb') or {}) if isinstance(logo_obj, dict) else {}
            url_l = thumb.get('url') if isinstance(thumb, dict) else None
            if url_l:
                logo = ('https:' + url_l) if url_l.startswith('//') else url_l

            # Taille entreprise (depuis WelcomeKit org.size ou nb_employees)
            nb_emp = h.get('nb_employees')
            if not nb_emp:
                size_obj = org.get('size') or {}
                size_fr  = size_obj.get('fr', '') if isinstance(size_obj, dict) else ''
                nb_emp   = _wk_parse_size(size_fr)
            if nb_emp:
                _cache_size(company, int(nb_emp))

            jobs.append({
                'id':          800000 + len(jobs),
                'title':       title,
                'company':     company,
                'link':        link,
                'desc':        re.sub(r'<[^>]+>', ' ', h.get('profile') or '').strip()[:200],
                'location':    location,
                'category':    categorize(title, ''),
                'daysAgo':     age,
                'logo':        logo,
                'company_size': int(nb_emp) if nb_emp else None,
                'isESN':       is_esn_company(company),
                'isCabinet':   is_cabinet(company),
                'source':      source_id,
            })

        page += 1
        if page < nb_pages:
            time.sleep(0.5)

    print(f'  [{display_name}] {len(jobs)} CDI')
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
                    'summary', 'objectID', 'nb_employees',
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
                if not org_slug:
                    continue  # skip jobs without a valid URL
                # Link to company jobs page (stable) — individual job URLs expire when filled
                link = f'{WTTJ_BASE}/fr/companies/{org_slug}/jobs'

                profession = (hit.get('new_profession') or {}).get('sub_category_name', '')
                desc = (hit.get('summary') or '')[:200]
                nb_emp = org.get('nb_employees') or hit.get('nb_employees')
                _cache_size(company, nb_emp)

                jobs.append({
                    'id':           1200000 + len(jobs),
                    'title':        title,
                    'company':      company,
                    'link':         link,
                    'desc':         desc,
                    'location':     _wttj_normalize_location(hit),
                    'category':     categorize(title, profession),
                    'daysAgo':      _wttj_days_ago(hit),
                    'isESN':        is_esn_company(company),
                    'isCabinet':    is_cabinet(company),
                    'source':       'wttj',
                    'company_size': int(nb_emp) if nb_emp else None,
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

    print('Fetch Fonds d\'investissements (WelcomeKit)...')
    for (fname, fid, furl) in FUND_BOARDS:
        try:
            fj = fetch_welcomekit(fname, fid, furl)
            jobs += fj
        except Exception as e:
            print(f'  {fname} erreur: {e}')

    print('Fetch Fonds d\'investissements (Getro)...')
    for (fname, fid, fnet, furl) in GETRO_BOARDS:
        try:
            fj = fetch_getro(fname, fid, fnet, furl)
            jobs += fj
        except Exception as e:
            print(f'  {fname} erreur: {e}')

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

    print('Enrichissement taille entreprises...')
    try:
        enrich_company_size(jobs)
    except Exception as e:
        print(f'  Taille entreprise erreur: {e}')
        for j in jobs:
            j.setdefault('company_size', None)

    updated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    template = open('template.html', encoding='utf-8').read()
    html = (template
            .replace('__JOBS__', json.dumps(jobs, ensure_ascii=False))
            .replace('"__UPDATED__"', f'"{updated}"'))

    os.makedirs('docs', exist_ok=True)
    open('docs/index.html', 'w', encoding='utf-8').write(html)
    print('docs/index.html généré')
