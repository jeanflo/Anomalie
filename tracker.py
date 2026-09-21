import os
import re
import json
import time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

NEWS_URL = "https://ingress.com/news"
OUTPUT_DIR = "public"

TRANSLATIONS = {
    "fr": {
        "lang_code": "fr",
        "switch_lang": "en",
        "switch_label": "🇬🇧 English",
        "switch_url": "en/",
        "hub_title": "XM Anomaly Hub",
        "hub_subtitle": "Suivi centralisé et synthèses des saisons d'anomalies Ingress",
        "back": "← Retour au Hub",
        "official_article": "📄 Article Officiel Niantic",
        "last_update": "Dernière actualisation le",
        "waiting": "⏳ En attente",
        "tie": "Égalité",
        "res_lead": "Avance RES",
        "enl_lead": "Avance ENL",
        "res_win": "Victoire RES",
        "enl_win": "Victoire ENL",
        "badge_live": "🔴 EN DIRECT",
        "badge_upcoming": "🟡 PROCHAINEMENT",
        "scores_pending": "Scores à venir",
        "global_victories": "Palmarès Global des Saisons",
        "victories_enl": "Victoires ENL",
        "victories_res": "Victoires RES",
        "ties": "Égalités",
        "global_res_lead": "🔵 <strong>La Résistance mène</strong> avec <strong>{res}</strong> contre <strong>{enl}</strong> pts (+{diff} pts)",
        "global_enl_lead": "🟢 <strong>Les Éclairés mènent</strong> avec <strong>{enl}</strong> contre <strong>{res}</strong> pts (+{diff} pts)",
        "global_res_won": "🔵 <strong>La Résistance remporte la saison</strong> avec <strong>{res}</strong> contre <strong>{enl}</strong> pts (+{diff} pts)",
        "global_enl_won": "🟢 <strong>Les Éclairés remportent la saison</strong> avec <strong>{enl}</strong> contre <strong>{res}</strong> pts (+{diff} pts)",
        "global_tie": "⚪ <strong>Égalité parfaite</strong> : {enl} pts",
        "season_overview": "Synthèse Générale de la Saison",
        "city_results": "Résultats des Villes Principales",
        "global_ops_title": "Opérations Globales (Global Ops)",
        "ifs_title": "Ingress First Saturday (IFS)",
        "col_event": "Épreuve / Ville",
        "col_enl": "🟢 Éclairés (ENL)",
        "col_res": "🔵 Résistance (RES)",
        "col_winner": "Vainqueur",
        "col_category": "Discipline / Phase",
        "total_partial": "TOTAL CUMULÉ",
        "total_site": "Total du Site",
        "total_fs": "Total Season Points IFS",
        "date_format": "%d/%m/%Y à %H:%M:%S"
    },
    "en": {
        "lang_code": "en",
        "switch_lang": "fr",
        "switch_label": "🇫🇷 Français",
        "switch_url": "../",
        "hub_title": "XM Anomaly Hub",
        "hub_subtitle": "Centralized tracking and summaries of Ingress anomaly seasons",
        "back": "← Back to Hub",
        "official_article": "📄 Official Niantic Article",
        "last_update": "Last updated on",
        "waiting": "⏳ Pending",
        "tie": "Tie",
        "res_lead": "RES Lead",
        "enl_lead": "ENL Lead",
        "res_win": "RES Victory",
        "enl_win": "ENL Victory",
        "badge_live": "🔴 LIVE",
        "badge_upcoming": "🟡 UPCOMING",
        "scores_pending": "Scores coming soon",
        "global_victories": "Overall Season Standings",
        "victories_enl": "ENL Victories",
        "victories_res": "RES Victories",
        "ties": "Ties",
        "global_res_lead": "🔵 <strong>The Resistance leads</strong> with <strong>{res}</strong> against <strong>{enl}</strong> pts (+{diff} pts)",
        "global_enl_lead": "🟢 <strong>The Enlightened lead</strong> with <strong>{enl}</strong> against <strong>{res}</strong> pts (+{diff} pts)",
        "global_res_won": "🔵 <strong>The Resistance won the season</strong> with <strong>{res}</strong> against <strong>{enl}</strong> pts (+{diff} pts)",
        "global_enl_won": "🟢 <strong>The Enlightened won the season</strong> with <strong>{enl}</strong> against <strong>{res}</strong> pts (+{diff} pts)",
        "global_tie": "⚪ <strong>Perfect tie</strong>: {enl} pts",
        "season_overview": "Season Overview",
        "city_results": "Primary Site Results",
        "global_ops_title": "Global Operations (Global Ops)",
        "ifs_title": "Ingress First Saturday (IFS)",
        "col_event": "Event / City",
        "col_enl": "🟢 Enlightened (ENL)",
        "col_res": "🔵 Resistance (RES)",
        "col_winner": "Winner",
        "col_category": "Discipline / Phase",
        "total_partial": "CUMULATIVE TOTAL",
        "total_site": "Site Total",
        "total_fs": "Total IFS Season Points",
        "date_format": "%Y-%m-%d at %H:%M:%S"
    }
}

SEASON_BANNERS = {
    "2026-apollo": "https://lh3.googleusercontent.com/9Xqw0Ndsgt-DZBO9XSccBaRkk8LjH3ok0Hd83Yme8vr_tdUDd3CRIkedNHKvHxm8X2JB2Kg5Od9eHLEY2NAbVDvePwHjGH22SgQ=e365-pa-nu-w1200",
    "2026-orion": "https://lh3.googleusercontent.com/4z82qZ5V5V4J0X3eF6P8D0G_sF8r4P6a5=e365-pa-nu-w1200",
    "2026-plusgamma": "https://lh3.googleusercontent.com/v_gamma=e365-pa-nu-w1200"
}

HISTORICAL_SEASONS = {
    "2026-plusgamma": {
        "title": {"fr": "+Gamma (2026)", "en": "+Gamma (2026)"},
        "url": "https://ingress.com/news/2026-plusgamma-results",
        "status": "archived",
        "banner": "https://lh3.googleusercontent.com/9Xqw0Ndsgt-DZBO9XSccBaRkk8LjH3ok0Hd83Yme8vr_tdUDd3CRIkedNHKvHxm8X2JB2Kg5Od9eHLEY2NAbVDvePwHjGH22SgQ=e365-pa-nu-w1200",
        "season_overview": [
            {"name": "Lisbon", "enl": "168.0", "res": "132.0"},
            {"name": "Charlotte", "enl": "176.6", "res": "123.4"},
            {"name": "Hong Kong", "enl": "165.0", "res": "135.0"},
            {"name": "Zagreb", "enl": "170.0", "res": "130.0"},
            {"name": "Hyderabad", "enl": "165.4", "res": "134.6"},
            {"name": "Buenos Aires", "enl": "170.0", "res": "130.0"},
            {"name": "+Gamma Global Op", "enl": "487.8", "res": "512.2"},
            {"name": "First Saturday", "enl": "300.0", "res": "300.0"}
        ],
        "enl_total": 1802.8,
        "res_total": 1597.2,
        "sites": [],
        "global_ops": [],
        "ifs": []
    },
    "2025-plusbeta": {
        "title": {"fr": "+Beta (2025)", "en": "+Beta (2025)"},
        "url": "https://ingress.com/news/2025-plusbeta-results",
        "status": "archived",
        "banner": "https://lh3.googleusercontent.com/9Xqw0Ndsgt-DZBO9XSccBaRkk8LjH3ok0Hd83Yme8vr_tdUDd3CRIkedNHKvHxm8X2JB2Kg5Od9eHLEY2NAbVDvePwHjGH22SgQ=e365-pa-nu-w1200",
        "season_overview": [
            {"name": "+Beta Global Op", "enl": "970.2", "res": "1029.8"},
            {"name": "Sendai", "enl": "163.0", "res": "137.0"},
            {"name": "San Diego", "enl": "141.0", "res": "159.0"},
            {"name": "Lyon", "enl": "146.0", "res": "154.0"},
            {"name": "Kaohsiung", "enl": "173.0", "res": "127.0"},
            {"name": "+Beta Connected Cells", "enl": "967.0", "res": "613.0"}
        ],
        "enl_total": 2560.2,
        "res_total": 2219.8,
        "sites": [],
        "global_ops": [],
        "ifs": []
    },
    "2025-plusdelta": {
        "title": {"fr": "+Delta (2025)", "en": "+Delta (2025)"},
        "url": "https://ingress.com/news/2025-plusdelta-results",
        "status": "archived",
        "banner": "https://lh3.googleusercontent.com/9Xqw0Ndsgt-DZBO9XSccBaRkk8LjH3ok0Hd83Yme8vr_tdUDd3CRIkedNHKvHxm8X2JB2Kg5Od9eHLEY2NAbVDvePwHjGH22SgQ=e365-pa-nu-w1200",
        "season_overview": [
            {"name": "+Delta Global Op", "enl": "981.2", "res": "1018.8"},
            {"name": "Kobe", "enl": "146.0", "res": "154.0"},
            {"name": "Madrid", "enl": "138.0", "res": "162.0"},
            {"name": "Washington DC", "enl": "128.0", "res": "172.0"}
        ],
        "enl_total": 1393.2,
        "res_total": 1306.8,
        "sites": [],
        "global_ops": [],
        "ifs": []
    },
    "2023-discoverie": {
        "title": {"fr": "Discoverie (2023)", "en": "Discoverie (2023)"},
        "url": "https://ingress.com/news/discoverie-rules",
        "status": "archived",
        "season_overview": [
            {"name": "Phase 1 (Madrid, Taichung, Curitiba)", "enl": "539.0", "res": "461.0"},
            {"name": "Phase 2 (Kinetic Challenge Op)", "enl": "49.0%", "res": "51.0% (x1.331)"},
            {"name": "Phase 3 (Bangkok, Palermo, Atlanta)", "enl": "549.0", "res": "600.0"},
            {"name": "Phase 4 (Reclaimer Challenge Op)", "enl": "49.9%", "res": "50.1% (x1.331)"},
            {"name": "Phase 5 (Honolulu, İzmir, Colombo)", "enl": "616.0", "res": "511.0"}
        ],
        "enl_total": 1704.0,
        "res_total": 1572.0,
        "sites": [],
        "global_ops": [],
        "ifs": []
    },
    "2023-ctrl": {
        "title": {"fr": "Ctrl (2023)", "en": "Ctrl (2023)"},
        "url": "https://ingress.com/news/ctrl-rules",
        "status": "archived",
        "season_overview": [
            {"name": "Phase 1 (Santa Cruz, Bandung, Rotenburg)", "enl": "509.0", "res": "467.0"},
            {"name": "Phase 2 (Oslo, Songpa, Charleston)", "enl": "507.0", "res": "460.0"},
            {"name": "Phase 3 (Kobe, Reims, Tacoma)", "enl": "656.0", "res": "334.0"}
        ],
        "enl_total": 1672.0,
        "res_total": 1261.0,
        "sites": [],
        "global_ops": [],
        "ifs": []
    },
    "2023-echo": {
        "title": {"fr": "Echo (2023)", "en": "Echo (2023)"},
        "url": "https://ingress.com/news/echo-rules",
        "status": "archived",
        "season_overview": [
            {"name": "Phase 1 (Jacksonville, Baguio, Pietermaritzburg)", "enl": "666.0", "res": "249.0"},
            {"name": "Phase 2 (Brisbane, Brighton, Montevideo)", "enl": "585.0", "res": "335.0"},
            {"name": "Phase 3 (Athens, Ueda, Winnipeg)", "enl": "585.0", "res": "310.0"}
        ],
        "enl_total": 1836.0,
        "res_total": 894.0,
        "sites": [],
        "global_ops": [],
        "ifs": []
    },
    "2022-epiphany-dawn": {
        "title": {"fr": "Epiphany Dawn (2022)", "en": "Epiphany Dawn (2022)"},
        "url": "https://ingress.com/news/epiphany-dawn-rules",
        "status": "archived",
        "season_overview": [
            {"name": "Phase 1 & Connected Cells", "enl": "412.0", "res": "488.0"},
            {"name": "Phase 2 (Los Angeles, Porto)", "enl": "380.0", "res": "420.0"},
            {"name": "Phase 3 (Yokohama)", "enl": "512.0", "res": "688.0"}
        ],
        "enl_total": 1304.0,
        "res_total": 1596.0,
        "sites": [],
        "global_ops": [],
        "ifs": []
    },
    "2022-kythera": {
        "title": {"fr": "Kythera (2022)", "en": "Kythera (2022)"},
        "url": "https://ingress.com/news/kythera3-results",
        "status": "archived",
        "season_overview": [
            {"name": "Phase 1 (Final Report)", "enl": "620.0", "res": "580.0"},
            {"name": "Phase 2 (Final Report)", "enl": "122.0", "res": "138.0"},
            {"name": "Phase 3 (Final Report)", "enl": "920.5", "res": "761.5"}
        ],
        "enl_total": 1662.5,
        "res_total": 1479.5,
        "sites": [],
        "global_ops": [],
        "ifs": []
    }
}

QUARTER_ORDER = [
    "cygnus", "plusbeta", "discoverie",
    "apollo", "ctrl",
    "orion", "echo",
    "plusgamma", "plusdelta", "epiphany-dawn", "kythera"
]


def clean_text(cell):
    return cell.get_text(strip=True).replace("\xa0", " ")


def normalize_city_name(name):
    clean = re.sub(r"^(?:anomaly\s*[-–—:]\s*|site\s*:\s*)", "", name, flags=re.IGNORECASE)
    return clean.strip()


def get_slug_sort_score(slug):
    parts = slug.split("-")
    year = int(parts[0]) if parts[0].isdigit() else 2020
    name = "-".join(parts[1:]).lower() if len(parts) > 1 else slug.lower()

    quarter_rank = 99
    for idx, q in enumerate(QUARTER_ORDER):
        if q in name:
            quarter_rank = idx
            break

    return (-year, quarter_rank)


def discover_anomaly_seasons(max_pages=3):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    discovered = {}

    for page in range(1, max_pages + 1):
        page_url = f"{NEWS_URL}?page={page}" if page > 1 else NEWS_URL
        try:
            res = requests.get(page_url, headers=headers, timeout=15)
            if res.status_code != 200:
                break
            soup = BeautifulSoup(res.text, "html.parser")
            links = soup.find_all("a", href=True)

            for a in links:
                href = a["href"].strip()
                title_lower = clean_text(a).lower()
                href_lower = href.lower()

                has_anomaly = "anomaly" in title_lower or "anomaly" in href_lower
                has_results = any(k in title_lower or k in href_lower for k in ["result", "score"])
                has_overview = any(k in title_lower or k in href_lower for k in ["overview", "schedule", "rule"])

                is_results = has_anomaly and has_results
                is_overview = has_anomaly and has_overview

                if not (is_results or is_overview):
                    continue

                match_slug = re.search(r"/news/([^/?#]+)", href)
                if not match_slug:
                    continue

                raw_slug = match_slug.group(1)
                if any(bad in raw_slug.lower() for bad in ["anomalysites", "guidelines", "faq", "instability"]):
                    continue

                slug = re.sub(r"-(?:results|overview|rules|schedule)$", "", raw_slug, flags=re.IGNORECASE)

                full_url = href if href.startswith("http") else f"https://ingress.com{href}"
                parts = slug.split("-")
                year = parts[0] if parts[0].isdigit() else ""
                raw_name = " ".join(parts[1:]) if len(parts) > 1 else slug
                clean_name = raw_name.replace("plus", "+").title()
                display_title = f"{clean_name} ({year})" if year else clean_name

                if is_results:
                    discovered[slug] = {
                        "title": {"fr": display_title, "en": display_title},
                        "url": full_url,
                        "status": "active"
                    }
                elif is_overview and slug not in discovered:
                    discovered[slug] = {
                        "title": {"fr": display_title, "en": display_title},
                        "url": full_url,
                        "status": "upcoming"
                    }

        except Exception as e:
            print(f"Erreur page {page} : {e}")
            break

    for h_slug, h_data in HISTORICAL_SEASONS.items():
        discovered[h_slug] = h_data

    return discovered


def fetch_raw_data(url, status, slug):
    if slug in HISTORICAL_SEASONS:
        hist = HISTORICAL_SEASONS[slug]
        banner = hist.get("banner", SEASON_BANNERS.get(slug, "https://lh3.googleusercontent.com/9Xqw0Ndsgt-DZBO9XSccBaRkk8LjH3ok0Hd83Yme8vr_tdUDd3CRIkedNHKvHxm8X2JB2Kg5Od9eHLEY2NAbVDvePwHjGH22SgQ=e365-pa-nu-w1200"))
        return {
            "banner": banner,
            "season_overview": hist["season_overview"],
            "sites": hist.get("sites", []),
            "global_ops": hist.get("global_ops", []),
            "ifs": hist.get("ifs", []),
            "has_pending_scores": False,
            "is_upcoming": False,
            "preset_totals": (hist["enl_total"], hist["res_total"])
        }

    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    banner = SEASON_BANNERS.get(slug, "https://lh3.googleusercontent.com/9Xqw0Ndsgt-DZBO9XSccBaRkk8LjH3ok0Hd83Yme8vr_tdUDd3CRIkedNHKvHxm8X2JB2Kg5Od9eHLEY2NAbVDvePwHjGH22SgQ=e365-pa-nu-w1200")

    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        html_text = res.text
        soup = BeautifulSoup(html_text, "html.parser")

        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_image and og_image.get("content"):
            found_banner = og_image["content"].strip()
            if found_banner.startswith("/"):
                found_banner = f"https://ingress.com{found_banner}"
            banner = found_banner
    except Exception as e:
        print(f"Erreur chargement pour {slug} ({url}) : {e}")
        html_text = ""
        soup = BeautifulSoup("", "html.parser")

    if status == "upcoming":
        return {
            "banner": banner,
            "season_overview": [],
            "sites": [],
            "global_ops": [],
            "ifs": [],
            "has_pending_scores": False,
            "is_upcoming": True
        }

    season_overview_raw = []
    global_ops_raw = []
    ifs_raw = []
    has_pending_scores = False

    # 1. Extraction exhaustive des tableaux
    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue
        headers_text = [clean_text(th).lower() for th in header_row.find_all(["th", "td"])]

        # Tableaux de sites
        if len(headers_text) >= 3 and any("site" in h for h in headers_text[:2]) and any("enlightened" in h for h in headers_text) and any("resistance" in h for h in headers_text):
            for r in table.find_all("tr")[1:]:
                cols = [clean_text(td) for td in r.find_all(["td", "th"])]
                if len(cols) >= 3:
                    name_raw = cols[0].strip()
                    if any(bad in name_raw.lower() for bad in ["season points", "total points", "total", ""]):
                        continue
                    enl_v = cols[1].strip()
                    res_v = cols[2].strip()

                    if enl_v in ["??", "???", "TBD", "-"] or res_v in ["??", "???", "TBD", "-"]:
                        enl_v = "??"
                        res_v = "??"
                        has_pending_scores = True

                    norm_name = normalize_city_name(name_raw)
                    if not any(normalize_city_name(item["name"]).lower() == norm_name.lower() for item in season_overview_raw):
                        season_overview_raw.append({
                            "name": norm_name,
                            "enl": enl_v,
                            "res": res_v
                        })

        # First Saturday & Global Ops
        elif len(headers_text) >= 3 and ("event" in headers_text[0] or "events" in headers_text[0]):
            table_text = table.get_text().lower()
            is_fs_table = "first saturday" in table_text or "participants" in table_text
            table_has_pending = False
            pending_label = ""
            total_row = None

            for r in table.find_all("tr")[1:]:
                cols = [clean_text(td) for td in r.find_all(["td", "th"])]
                if len(cols) >= 3:
                    row_label = cols[0].strip()
                    val_enl = cols[1].strip()
                    val_res = cols[2].strip()

                    if "??" in val_enl or "??" in val_res or "tbd" in val_enl.lower():
                        table_has_pending = True
                        has_pending_scores = True
                        if "september" in row_label.lower():
                            pending_label = "Sept. en attente"

                    if is_fs_table:
                        ifs_raw.append({"phase": row_label, "enl": val_enl, "res": val_res})
                    else:
                        global_ops_raw.append({"event": row_label, "enl": val_enl, "res": val_res})

                    if any(k in row_label.lower() for k in ["total", "season points total"]):
                        total_row = (row_label, val_enl, val_res)

            if total_row:
                row_label, enl_v, res_v = total_row
                event_title = "First Saturday" if is_fs_table else "Global Op"
                enl_clean = enl_v.replace(",", "").strip()
                res_clean = res_v.replace(",", "").strip()

                if table_has_pending:
                    suffix = f" ({pending_label})" if pending_label else " (en attente)"
                    display_title = f"{event_title}{suffix}"
                else:
                    display_title = event_title

                if not any(item["name"].lower() == display_title.lower() for item in season_overview_raw):
                    season_overview_raw.append({
                        "name": display_title,
                        "enl": enl_clean,
                        "res": res_clean
                    })

    # 2. Parsing détaillé des sections "Site: [Nom]"
    sites_raw = []
    site_headers = soup.find_all(re.compile(r"^h[2-4]$"), string=re.compile(r"Site:\s*([A-Za-zÀ-ÿ\s\-]+)", re.IGNORECASE))

    for sh in site_headers:
        m = re.search(r"Site:\s*([A-Za-zÀ-ÿ\s\-]+)", sh.get_text(), re.IGNORECASE)
        if not m:
            continue
        site_name = m.group(1).strip()
        norm_site = normalize_city_name(site_name)

        site_dict = {
            "name": site_name,
            "enl_pts": "??",
            "res_pts": "??",
            "stealth_ops": {"enl": "0.0", "res": "0.0"},
            "urban_ops": {"enl": "0.0", "res": "0.0"},
            "shards": {"enl": "??", "res": "??"},
            "beacons": {"enl": "??", "res": "??"},
            "uniques": {"enl": "??", "res": "??"}
        }

        ov_match = next((item for item in season_overview_raw if normalize_city_name(item["name"]).lower() == norm_site.lower()), None)
        if ov_match:
            site_dict["enl_pts"] = ov_match["enl"]
            site_dict["res_pts"] = ov_match["res"]

        curr = sh.next_sibling
        current_context = ""
        safety_counter = 0

        while curr and safety_counter < 300:
            safety_counter += 1
            if hasattr(curr, "name") and curr.name in ["h2", "h3", "h1"]:
                break

            if hasattr(curr, "get_text"):
                txt = curr.get_text().strip().lower()
                if "stealth ops" in txt:
                    current_context = "stealth"
                elif "urban ops" in txt:
                    current_context = "urban"
                elif "shard battle" in txt:
                    current_context = "shard"
                elif "beacon battle" in txt:
                    current_context = "beacon"

            if hasattr(curr, "name") and curr.name == "table":
                rows = curr.find_all("tr")
                t_head = rows[0].get_text().lower() if rows else ""
                if "stealth" in t_head:
                    current_context = "stealth"
                elif "urban" in t_head:
                    current_context = "urban"
                elif "shards" in t_head:
                    current_context = "shard"
                elif "wave number" in t_head:
                    current_context = "beacon"
                elif "anomaly uniques" in t_head:
                    current_context = "unique"

                for r in rows:
                    cols = [clean_text(td) for td in r.find_all(["td", "th"])]
                    if not cols:
                        continue

                    if any("season points" in c.lower() for c in cols):
                        if current_context == "shard" and len(cols) >= 7:
                            site_dict["shards"] = {"enl": cols[5], "res": cols[6]}
                        elif len(cols) >= 3:
                            val_e = cols[1]
                            val_r = cols[2]
                            if current_context == "stealth":
                                site_dict["stealth_ops"] = {"enl": val_e, "res": val_r}
                            elif current_context == "urban":
                                site_dict["urban_ops"] = {"enl": val_e, "res": val_r}
                            elif current_context == "beacon":
                                site_dict["beacons"] = {"enl": val_e, "res": val_r}
                            elif current_context == "unique":
                                site_dict["uniques"] = {"enl": val_e, "res": val_r}

                if current_context == "unique":
                    current_context = ""

            curr = curr.next_sibling

        if site_dict["enl_pts"] == "??" or site_dict["res_pts"] == "??":
            try:
                tot_e = (
                    float(site_dict["stealth_ops"]["enl"])
                    + float(site_dict["urban_ops"]["enl"])
                    + float(site_dict["shards"]["enl"])
                    + float(site_dict["beacons"]["enl"])
                    + float(site_dict["uniques"]["enl"])
                )
                tot_r = (
                    float(site_dict["stealth_ops"]["res"])
                    + float(site_dict["urban_ops"]["res"])
                    + float(site_dict["shards"]["res"])
                    + float(site_dict["beacons"]["res"])
                    + float(site_dict["uniques"]["res"])
                )
                site_dict["enl_pts"] = str(round(tot_e, 1))
                site_dict["res_pts"] = str(round(tot_r, 1))
            except ValueError:
                has_pending_scores = True

        sites_raw.append(site_dict)

        # RÈGLE D'OR : Si la ville n'était pas dans la synthèse du haut, on l'y ajoute immédiatement
        if not any(normalize_city_name(item["name"]).lower() == norm_site.lower() for item in season_overview_raw):
            season_overview_raw.append({
                "name": site_name,
                "enl": site_dict["enl_pts"],
                "res": site_dict["res_pts"]
            })

    return {
        "banner": banner,
        "season_overview": season_overview_raw,
        "sites": sites_raw,
        "global_ops": global_ops_raw,
        "ifs": ifs_raw,
        "has_pending_scores": has_pending_scores,
        "is_upcoming": False
    }


def process_season_for_lang(slug, info, raw_data, card_state, lang, t, env, now_iso):
    title = info["title"][lang]
    target_dir = OUTPUT_DIR if lang == "fr" else os.path.join(OUTPUT_DIR, "en")
    os.makedirs(target_dir, exist_ok=True)

    if card_state == "upcoming":
        return {
            "title": title,
            "slug": slug,
            "banner": raw_data["banner"],
            "html_file": info["url"],
            "enl": "—",
            "res": "—",
            "diff": 0,
            "lead_badge": t["badge_upcoming"],
            "badge_class": "badge-upcoming",
            "card_state": "upcoming"
        }

    season_overview = []
    enl_sum = 0.0
    res_sum = 0.0

    preset = raw_data.get("preset_totals")
    if preset:
        enl_sum, res_sum = preset

    for row in raw_data["season_overview"]:
        raw_name = row["name"]
        enl_val = str(row["enl"]).strip()
        res_val = str(row["res"]).strip()
        winner = "—"

        lower_name = raw_name.lower()
        if "first saturday" in lower_name or "satudays" in lower_name or "ifs" in lower_name:
            anchor_link = "#section-ifs"
        elif any(k in lower_name for k in ["global op", "link & field", "connected cells", "challenge"]):
            anchor_link = "#section-global-ops"
        else:
            norm_city = normalize_city_name(raw_name).lower().replace(" ", "-")
            anchor_link = f"#{norm_city}"

        if enl_val != "??" and res_val != "??":
            try:
                e = float(enl_val.replace(",", "").replace(" ", ""))
                r = float(res_val.replace(",", "").replace(" ", ""))
                if not preset:
                    enl_sum += e
                    res_sum += r
                winner = "🟢 ENL" if e > r else ("🔵 RES" if r > e else t["tie"])
            except ValueError:
                pass
        else:
            winner = t["waiting"]

        season_overview.append({
            "name": raw_name,
            "link": anchor_link,
            "enl": enl_val,
            "res": res_val,
            "winner": winner
        })

    enl_sum = round(enl_sum, 1)
    res_sum = round(res_sum, 1)
    diff = round(res_sum - enl_sum, 1)

    if diff > 0:
        lead_badge = f"{t['res_lead']} (+{diff})" if card_state == "live" else f"{t['res_win']} (+{diff})"
        status_tmpl = t["global_res_lead"] if card_state == "live" else t["global_res_won"]
        global_status = status_tmpl.format(res=res_sum, enl=enl_sum, diff=diff)
        badge_class = "badge-res"
    elif diff < 0:
        lead_badge = f"{t['enl_lead']} (+{round(-diff, 1)})" if card_state == "live" else f"{t['enl_win']} (+{round(-diff, 1)})"
        status_tmpl = t["global_enl_lead"] if card_state == "live" else t["global_enl_won"]
        global_status = status_tmpl.format(res=res_sum, enl=enl_sum, diff=round(-diff, 1))
        badge_class = "badge-enl"
    else:
        global_status = t["global_tie"].format(enl=enl_sum)
        lead_badge = t["tie"]
        badge_class = ""

    tmpl_detail = env.get_template("detail_template.html.j2")
    rendered_html = tmpl_detail.render(
        title=title,
        season_title=title,
        updated_at=now_iso,
        global_status=global_status,
        enl_total=enl_sum,
        res_total=res_sum,
        diff=diff,
        season_overview=season_overview,
        sites=raw_data.get("sites", []),
        global_ops=raw_data.get("global_ops", []),
        ifs=raw_data.get("ifs", []),
        t=t,
        slug=slug,
        official_url=info["url"]
    )

    with open(os.path.join(target_dir, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(rendered_html)

    return {
        "title": title,
        "slug": slug,
        "banner": raw_data["banner"],
        "html_file": f"{slug}.html",
        "enl": enl_sum,
        "res": res_sum,
        "diff": diff,
        "lead_badge": lead_badge,
        "badge_class": badge_class,
        "card_state": card_state
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "en"), exist_ok=True)
    env = Environment(loader=FileSystemLoader("."))

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    seasons = discover_anomaly_seasons()

    scraped_data = {}
    for slug, info in seasons.items():
        try:
            print(f"Scraping : {slug}...")
            data = fetch_raw_data(info["url"], info.get("status", "active"), slug)
            scraped_data[slug] = data
        except Exception as e:
            print(f"Erreur sur {slug} : {e}")

    sorted_slugs = sorted(scraped_data.keys(), key=get_slug_sort_score)

    active_slug = None
    for s_slug in sorted_slugs:
        info = seasons.get(s_slug, {})
        if info.get("status") not in ["upcoming", "archived"]:
            if scraped_data[s_slug].get("has_pending_scores"):
                active_slug = s_slug
                break

    for lang in ["fr", "en"]:
        t = TRANSLATIONS[lang]
        dest_dir = OUTPUT_DIR if lang == "fr" else os.path.join(OUTPUT_DIR, "en")

        hub_cards = []
        for slug, info in seasons.items():
            if slug in scraped_data:
                data = scraped_data[slug]
                if data.get("is_upcoming") or info.get("status") == "upcoming":
                    card_state = "upcoming"
                elif slug == active_slug:
                    card_state = "live"
                else:
                    card_state = "archived"

                card = process_season_for_lang(slug, info, data, card_state, lang, t, env, now_iso)
                hub_cards.append(card)

        enl_wins = 0
        res_wins = 0
        ties = 0

        for card in hub_cards:
            if card["card_state"] == "archived":
                if card["res"] > card["enl"]:
                    res_wins += 1
                elif card["enl"] > card["res"]:
                    enl_wins += 1
                else:
                    ties += 1

        total_completed = enl_wins + res_wins + ties
        enl_pct = round((enl_wins / total_completed) * 100, 1) if total_completed > 0 else 50.0
        res_pct = round((res_wins / total_completed) * 100, 1) if total_completed > 0 else 50.0

        standings = {
            "enl_wins": enl_wins,
            "res_wins": res_wins,
            "ties": ties,
            "total": total_completed,
            "enl_pct": enl_pct,
            "res_pct": res_pct
        }

        def sort_key(card):
            state_prio = {"upcoming": 0, "live": 1, "archived": 2}.get(card["card_state"], 3)
            chrono_score = get_slug_sort_score(card["slug"])
            return (state_prio, chrono_score)

        hub_cards.sort(key=sort_key)

        tmpl_hub = env.get_template("hub_template.html.j2")
        rendered_hub = tmpl_hub.render(
            seasons=hub_cards,
            standings=standings,
            t=t,
            updated_at=now_iso
        )

        with open(os.path.join(dest_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(rendered_hub)

    print("Actualisation du Hub terminée avec succès.")


if __name__ == "__main__":
    main()
