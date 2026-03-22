"""
find_tokens.py
==============
Tests Greenhouse board tokens for every company and sports team
discussed in this project. Run once, paste results into config.py.

Usage (from your Job_Search project root):
    python find_tokens.py

One-time utility — not part of the weekly pipeline.
Output at the bottom gives you a ready-to-paste block for config.py.
"""

import requests
import time

BASE = "https://boards-api.greenhouse.io/v1/boards/{}/jobs"

# (display label, [token candidates to try in order])
ALL_TARGETS = [

    # =========================================================================
    # STADIUM NAMING RIGHTS COMPANIES
    # =========================================================================

    ("American Family Ins",  ["americanfamily", "amfam", "americanfamilyinsurance"]),
    ("AB InBev (Busch)",     ["abinbev", "anheuserbuschinbev", "abinbevusa"]),
    ("Chase / JPMorgan",     ["jpmorgan", "jpmorganchase", "chase", "jpmc"]),
    ("Citi",                 ["citi", "citigroup", "citibank"]),
    ("Citizens Bank",        ["citizensbank", "citizensfinancial", "citizens"]),
    ("Comerica",             ["comerica", "comericabank"]),
    ("Molson Coors",         ["molsoncoors", "coors", "molsoncoorsbeverage"]),
    ("Daikin",               ["daikin", "daikincomfort", "daikinamerica"]),
    ("Globe Life",           ["globelife", "torchmark", "globe-life"]),
    ("Great American Ins",   ["greatamerican", "gaig", "great-american"]),
    ("Guaranteed Rate",      ["guaranteedrate", "rate", "guaranteed-rate"]),
    ("loanDepot",            ["loandepot", "loan-depot", "ldwholesale"]),
    ("Oracle",               ["oracle", "oraclecorp"]),
    ("Petco",                ["petco", "petcolovesanimals"]),
    ("PNC Bank",             ["pnc", "pncbank", "pncfinancial"]),
    ("Progressive",          ["progressive", "progressiveinsurance"]),
    ("Rogers",               ["rogers", "rogerscommuncations", "rogersbank"]),
    ("Target",               ["target", "targetcorporation", "targetcorp"]),
    ("T-Mobile",             ["tmobile", "t-mobile", "tmobileusa"]),
    ("Truist",               ["truist", "truistbank", "truistfinancial"]),
    ("Tropicana",            ["tropicana", "tropicanafieldoperations"]),
    ("Wrigley / Mars",       ["mars", "marsglobal", "marswrigley", "wrigley"]),
    ("State Farm",           ["statefarm", "state-farm"]),
    ("Mercedes-Benz",        ["mercedesbenz", "mercedesbenzusa", "mbusa"]),
    ("M&T Bank",             ["mandtbank", "mtbank", "mandtbankco"]),
    ("Highmark",             ["highmark", "highmarkhealth", "highmarkinc"]),
    ("Bank of America",      ["bankofamerica", "bofa", "bofasecurities"]),
    ("Huntington Bank",      ["huntington", "huntingtonbank", "huntingtonbancshares"]),
    ("Paycor",               ["paycor", "paycorinc"]),
    ("AT&T",                 ["att", "atandt", "at-t"]),
    ("Empower",              ["empower", "empowerretirement", "empowerfinancial"]),
    ("Ford",                 ["ford", "fordmotor", "fordmotorcompany"]),
    ("NRG Energy",           ["nrgenergy", "nrg"]),
    ("Lucas Oil",            ["lucasoil", "lucas-oil"]),
    ("GEHA",                 ["geha", "governmentemployees"]),
    ("SoFi",                 ["sofi", "sofitech"]),
    ("MetLife",              ["metlife", "metlifeinc"]),
    ("U.S. Bank",            ["usbank", "usbancorp", "us-bank"]),
    ("Hard Rock",            ["hardrock", "hardrockinternational", "seminolehardrock"]),
    ("Caesars",              ["caesars", "caesarsentertainment"]),
    ("Levi Strauss",         ["levistrauss", "levis", "levi"]),
    ("American Airlines",    ["americanairlines", "aa", "americanairlinesgroup"]),
    ("Barclays",             ["barclays", "barclaysus", "barclaysbank"]),
    ("Scotiabank",           ["scotiabank", "bns", "bankofnovascotia"]),
    ("TD Bank",              ["tdbank", "td", "tdfinancial"]),
    ("United Airlines",      ["unitedairlines", "united", "unitedcontinental"]),
    ("Rocket Mortgage",      ["rocketmortgage", "rocketcompanies", "quickenloans"]),
    ("Intuit",               ["intuit", "intuitinc"]),
    ("Gainbridge",           ["gainbridge", "grouponefinancial"]),
    ("Capital One",          ["capitalone", "capital-one", "capitalonefinancial"]),
    ("Kia America",          ["kiamotorsamerica", "kiaamerica", "kia"]),
    ("Crypto.com",           ["cryptocom", "crypto", "foris"]),
    ("KeyBank",              ["keybank", "keycorp", "key-corp"]),
    ("Comcast / Xfinity",    ["comcast", "xfinity", "nbcuniversal", "comcastnbcuniversal"]),
    ("Canada Life",          ["canadalife", "greatwestlifeco", "lifeco"]),
    ("Climate Pledge/Amazon",["amazon", "amazonjobs", "amazondevelopmentcenter"]),

    # =========================================================================
    # MSPs AND IT SOLUTION PROVIDERS
    # =========================================================================

    ("CDW",                  ["cdw", "cdwcorporation", "cdwg"]),
    ("Presidio",             ["presidio", "presidioinc"]),
    ("Atos",                 ["atos", "atosse", "atosorigin"]),
    ("Insight Global",       ["insightglobal", "insight-global"]),
    ("Ahead",                ["ahead", "aheadllc"]),
    ("Logicalis",            ["logicalis", "logicalisus"]),
    ("Trace3",               ["trace3", "trace-3"]),
    ("ePlus",                ["eplus", "eplustech"]),
    ("WWT",                  ["wwt", "worldwidetechnology", "world-wide-technology"]),
    ("Okta",                 ["okta", "oktainc"]),
    ("HashiCorp",            ["hashicorp", "hashi-corp"]),
    ("Datadog",              ["datadog", "datadoghq"]),
    ("PagerDuty",            ["pagerduty", "pager-duty"]),

    # =========================================================================
    # MLB TEAMS
    # =========================================================================

    ("Arizona Diamondbacks",  ["arizonadiamondbacks", "dbacks", "azdiamondbacks"]),
    ("Atlanta Braves",        ["atlantabraves", "braves"]),
    ("Baltimore Orioles",     ["baltimoreorioles", "orioles"]),
    ("Boston Red Sox",        ["bostonredsox", "redsox", "fenwaysports"]),
    ("Chicago Cubs",          ["chicagocubs", "cubs"]),
    ("Chicago White Sox",     ["chicagowhitesox", "whitesox"]),
    ("Cincinnati Reds",       ["cincinnatireds", "reds"]),
    ("Cleveland Guardians",   ["clevelandguardians", "guardians"]),
    ("Colorado Rockies",      ["coloradorockies", "rockies"]),
    ("Detroit Tigers",        ["detroittigers", "tigers"]),
    ("Houston Astros",        ["houstonastros", "astros"]),
    ("Kansas City Royals",    ["kansascityroyals", "royals"]),
    ("LA Angels",             ["losangelesangels", "angels", "laangels"]),
    ("LA Dodgers",            ["losangelesdodgers", "dodgers", "ladodgers"]),
    ("Miami Marlins",         ["miamimarlins", "marlins"]),
    ("Milwaukee Brewers",     ["milwaukeebrewers", "brewers"]),
    ("Minnesota Twins",       ["minnesotabtwins", "twins", "minnesotawins"]),
    ("New York Mets",         ["newyorkmets", "mets"]),
    ("New York Yankees",      ["newyorkyankees", "yankees"]),
    ("Oakland Athletics",     ["oaklandathletics", "athletics", "abaseball"]),
    ("Philadelphia Phillies", ["philadelphiaphillies", "phillies"]),
    ("Pittsburgh Pirates",    ["pittsburghpirates", "pirates"]),
    ("San Diego Padres",      ["sandiegopadres", "padres"]),
    ("San Francisco Giants",  ["sanfranciscogiants", "sfgiants", "sfgbaseball"]),
    ("Seattle Mariners",      ["seattlemariners", "mariners"]),
    ("St. Louis Cardinals",   ["stlouiscardinals", "cardinals", "stlcardinals"]),
    ("Tampa Bay Rays",        ["tampabayrays", "rays"]),
    ("Texas Rangers",         ["texasrangers", "rangers", "txrangers"]),
    ("Toronto Blue Jays",     ["torontobluejays", "bluejays"]),
    ("Washington Nationals",  ["washingtonnationalsss", "nationals", "washingtonnationals"]),

    # =========================================================================
    # NBA TEAMS
    # =========================================================================

    ("Atlanta Hawks",          ["atlantahawks", "hawks"]),
    ("Boston Celtics",         ["bostonceltics", "celtics"]),
    ("Brooklyn Nets",          ["brooklynnets", "nets"]),
    ("Charlotte Hornets",      ["charlottehornets", "hornets"]),
    ("Chicago Bulls",          ["chicagobulls", "bulls"]),
    ("Cleveland Cavaliers",    ["clevelandcavaliers", "cavaliers", "cavs"]),
    ("Dallas Mavericks",       ["dallasmavericks", "mavericks", "mavs"]),
    ("Denver Nuggets",         ["denvernuggets", "nuggets"]),
    ("Detroit Pistons",        ["detroitpistons", "pistons"]),
    ("Golden State Warriors",  ["goldenstatewarriors", "warriors", "gswarriors"]),
    ("Houston Rockets",        ["houstonrockets", "rockets"]),
    ("Indiana Pacers",         ["indianapacers", "pacers"]),
    ("LA Clippers",            ["laclippers", "clippers"]),
    ("LA Lakers",              ["losangeleslakers", "lakers", "lalakers"]),
    ("Memphis Grizzlies",      ["memphisgrizzlies", "grizzlies"]),
    ("Miami Heat",             ["miamiheat", "heat"]),
    ("Milwaukee Bucks",        ["milwaukeebucks", "bucks"]),
    ("Minnesota Timberwolves", ["minnesotatimberwolves", "timberwolves", "twolves"]),
    ("New Orleans Pelicans",   ["neworleanspelicans", "pelicans"]),
    ("New York Knicks",        ["newyorkknicks", "knicks"]),
    ("OKC Thunder",            ["oklahomacitythunder", "thunder", "okcthunder"]),
    ("Orlando Magic",          ["orlandomagic", "magic"]),
    ("Philadelphia 76ers",     ["philadelphia76ers", "76ers", "sixers"]),
    ("Phoenix Suns",           ["phoenixsuns", "suns"]),
    ("Portland Trail Blazers", ["portlandtrailblazers", "trailblazers", "blazers"]),
    ("Sacramento Kings",       ["sacramentokings", "kings", "sackings"]),
    ("San Antonio Spurs",      ["sanantoniospurs", "spurs"]),
    ("Toronto Raptors",        ["torontoraptors", "raptors"]),
    ("Utah Jazz",              ["utahjazz", "jazz"]),
    ("Washington Wizards",     ["washingtonwizards", "wizards"]),

    # =========================================================================
    # NFL TEAMS
    # =========================================================================

    ("Arizona Cardinals",      ["arizonacardinals", "azcardinals"]),
    ("Atlanta Falcons",        ["atlantafalcons", "falcons"]),
    ("Baltimore Ravens",       ["baltimoreravens", "ravens"]),
    ("Buffalo Bills",          ["buffalobills", "bills"]),
    ("Carolina Panthers",      ["carolinapanthers", "panthers", "cpanthers"]),
    ("Chicago Bears",          ["chicagobears", "bears"]),
    ("Cincinnati Bengals",     ["cincinnatibengals", "bengals"]),
    ("Cleveland Browns",       ["clevelandbrowns", "browns"]),
    ("Dallas Cowboys",         ["dallascowboys", "cowboys"]),
    ("Denver Broncos",         ["denverbroncos", "broncos"]),
    ("Detroit Lions",          ["detroitlions", "lions"]),
    ("Green Bay Packers",      ["greenbaypackers", "packers"]),
    ("Houston Texans",         ["houstontexans", "texans"]),
    ("Indianapolis Colts",     ["indianapoliscolts", "colts"]),
    ("Jacksonville Jaguars",   ["jacksonvillejaguars", "jaguars"]),
    ("Kansas City Chiefs",     ["kansascitychiefs", "chiefs"]),
    ("Las Vegas Raiders",      ["lasvegasraiders", "raiders"]),
    ("LA Chargers",            ["losangeleschargers", "chargers", "lachargers"]),
    ("LA Rams",                ["losangelesrams", "rams", "larams"]),
    ("Miami Dolphins",         ["miamidolphins", "dolphins"]),
    ("Minnesota Vikings",      ["minnesotavikings", "vikings"]),
    ("New England Patriots",   ["newenglandpatriots", "patriots"]),
    ("New Orleans Saints",     ["neworleanssaints", "saints"]),
    ("New York Giants",        ["newyorkgiants", "nygiants", "giants"]),
    ("New York Jets",          ["newyorkjets", "jets", "nyjets"]),
    ("Philadelphia Eagles",    ["philadelphiaeagles", "eagles"]),
    ("Pittsburgh Steelers",    ["pittsburghsteelers", "steelers"]),
    ("San Francisco 49ers",    ["sanfrancisco49ers", "49ers", "sf49ers"]),
    ("Seattle Seahawks",       ["seattleseahawks", "seahawks"]),
    ("Tampa Bay Buccaneers",   ["tampabaybuccaneers", "buccaneers", "bucs"]),
    ("Tennessee Titans",       ["tennesseetitans", "titans"]),
    ("Washington Commanders",  ["washingtoncommanders", "commanders"]),

    # =========================================================================
    # NHL TEAMS
    # =========================================================================

    ("Anaheim Ducks",           ["anaheimducks", "ducks"]),
    ("Boston Bruins",           ["bostonbruins", "bruins"]),
    ("Buffalo Sabres",          ["buffalosabres", "sabres"]),
    ("Calgary Flames",          ["calgaryflames", "flames"]),
    ("Carolina Hurricanes",     ["carolinahurricanes", "hurricanes", "canes"]),
    ("Chicago Blackhawks",      ["chicagoblackhawks", "blackhawks"]),
    ("Colorado Avalanche",      ["coloradoavalanche", "avalanche", "avs"]),
    ("Columbus Blue Jackets",   ["columbusbluejackets", "bluejackets"]),
    ("Dallas Stars",            ["dallasstars", "stars", "dallasstarshockey"]),
    ("Detroit Red Wings",       ["detroitredwings", "redwings"]),
    ("Edmonton Oilers",         ["edmontonoilers", "oilers"]),
    ("Florida Panthers",        ["floridapanthers", "flpanthers", "flapanthers"]),
    ("Vegas Golden Knights",    ["lasvegasgoldenknights", "goldenknights", "vgk"]),
    ("LA Kings",                ["losangeleskings", "lakings", "lakingshockey"]),
    ("Minnesota Wild",          ["minnesotawild", "wild", "mnwild"]),
    ("Montreal Canadiens",      ["montrealcanadiens", "canadiens", "habs"]),
    ("Nashville Predators",     ["nashvillepredators", "predators", "preds"]),
    ("New Jersey Devils",       ["newjerseydevils", "devils"]),
    ("New York Islanders",      ["newyorkislanders", "islanders"]),
    ("New York Rangers",        ["newyorkrangers", "rangers", "nyrangers"]),
    ("Ottawa Senators",         ["ottawasenators", "senators"]),
    ("Philadelphia Flyers",     ["philadelphiaflyers", "flyers"]),
    ("Pittsburgh Penguins",     ["pittsburghpenguins", "penguins", "pens"]),
    ("San Jose Sharks",         ["sanjosesharks", "sharks"]),
    ("Seattle Kraken",          ["seattlekraken", "kraken"]),
    ("St. Louis Blues",         ["stlouisblues", "blues", "stlblues"]),
    ("Tampa Bay Lightning",     ["tampalightning", "lightning", "tblightning"]),
    ("Toronto Maple Leafs",     ["torontomapleleafs", "mapleleafs", "leafs"]),
    ("Utah Hockey Club",        ["utahhockeyclub", "utahhc", "utahhockey"]),
    ("Vancouver Canucks",       ["vancouvercanucks", "canucks"]),
    ("Washington Capitals",     ["washingtoncapitals", "capitals", "caps"]),
    ("Winnipeg Jets",           ["winnipegjets", "jets", "wpgjets"]),
]

# ─────────────────────────────────────────────────────────────────────────────

print(f"Testing {len(ALL_TARGETS)} targets — this takes about {len(ALL_TARGETS) // 5} seconds...\n")

valid   = []
invalid = []

for label, tokens in ALL_TARGETS:
    matched = None
    for token in tokens:
        try:
            r = requests.get(BASE.format(token), timeout=8)
            if r.status_code == 200:
                count = len(r.json().get("jobs", []))
                print(f"  FOUND    {label:30s}  token={token}  ({count} jobs)")
                matched = token
                break
        except requests.RequestException as e:
            print(f"  ERROR    {label}: {e}")
            break
        time.sleep(0.2)

    if matched:
        valid.append((label, matched))
    else:
        invalid.append(label)

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

print(f"\n{'=' * 65}")
print(f"Found:     {len(valid)} / {len(ALL_TARGETS)}")
print(f"Not found: {len(invalid)}\n")

print("─" * 65)
print("Ready to paste into GREENHOUSE_COMPANIES in config.py:")
print("─" * 65 + "\n")

# Group output by section for easier pasting
sections = [
    ("Stadium naming rights companies", 0,   53),
    ("MSPs and IT solution providers",  53,  66),
    ("MLB teams",                       66,  96),
    ("NBA teams",                       96,  126),
    ("NFL teams",                       126, 158),
    ("NHL teams",                       158, 190),
]

# Build a lookup so we can group valid results by section
target_labels = [label for label, _ in ALL_TARGETS]

for section_name, start, end in sections:
    section_labels = {label for label, _ in ALL_TARGETS[start:end]}
    section_valid  = [(l, t) for l, t in valid if l in section_labels]
    if section_valid:
        print(f"    # --- {section_name} ---")
        for label, token in section_valid:
            print(f'    {{"label": "{label}", "token": "{token}"}},')
        print()

print("─" * 65)
if invalid:
    print(f"\nNot found on Greenhouse ({len(invalid)} targets):")
    print("These use Workday, Oracle HCM, or another ATS.\n")
    for label in invalid:
        print(f"  {label}")
