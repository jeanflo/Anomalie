import os
import re
import json
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
import markdown
import time

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
        "global_tie": "⚪ <strong>Égalité parfaite</strong> : {enl} pts",
        "season_overview": "Tableau récapitulatif de la saison",
        "city_results": "Résultats par Ville / Phase",
        "col_event": "Épreuve / Événement",
        "col_enl": "🟢 Éclairés (ENL)",
        "col_res": "🔵 Résistance (RES)",
        "col_winner": "Vainqueur",
        "col_category": "Catégorie",
        "total_partial": "TOTAL FINAL",
        "total_site": "Total Site",
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
        "global_tie": "⚪ <strong>Perfect tie</strong>: {enl} pts",
        "season_overview": "Season Overview",
        "city_results": "Results by City / Phase",
        "col_event": "Event / Phase",
        "col_enl": "🟢 Enlightened (ENL)",
        "col_res": "🔵 Resistance (RES)",
        "col_winner": "Winner",
        "col_category": "Category",
        "total_partial": "FINAL TOTAL",
        "total_site": "Site Total",
        "date_format": "%Y-%m-%d at %H:%M:%S"
    }
}

# Données validées pour les saisons passées
HISTORICAL_SEASONS = {
    "2025-plusbeta": {
        "title": {"fr": "+Beta (2025)", "en": "+Beta (2025)"},
        "url": "https://ingress.com/news/2025-plusbeta-results",
        "status": "archived",
        "season_overview": [
            {"name": "+Beta Global Op", "enl": "970.2", "res": "1029.8"},
            {"name": "Site: Sendai", "enl": "163.0", "res": "137.0"},
            {"name": "Site: San Diego", "enl": "141.0", "res": "159.0"},
            {"name": "Site: Lyon", "enl": "146.0", "res": "154.0"},
            {"name": "Site: Kaohsiung", "enl": "173.0", "res": "127.0"},
            {"name": "+Beta Connected Cells", "enl": "967.0", "res": "613.0"}
        ],
        "enl_total": 2560.2,
        "res_total": 2219.8
    },
    "2025-plusdelta": {
        "title": {"fr": "+Delta (2025)", "en": "+Delta (2025)"},
        "url": "https://ingress.com/news/2025-plusdelta-results",
        "status": "archived",
        "season_overview": [
            {"name": "+Delta Global Op", "enl": "981.2", "res": "1018.8"},
            {"name": "Site: Kobe", "enl": "146.0", "res": "154.0"},
            {"name": "Site: Madrid", "enl": "138.0", "res": "162.0"},
            {"name": "Site: Washington DC", "enl": "128.0", "res": "172.0"}
        ],
        "enl_total": 1393.2,
        "res_total": 1306.8
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
        "res_total": 1572.0
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
        "res_total": 1261.0
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
        "res_total": 894.0
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
        "res_total": 1596.0
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
        "res_total": 1479.5
    }
}


def clean_text(cell):
    return cell.get_text(strip=True).replace("\xa0", " ")


def normalize_city_name(name):
    clean = re.sub(r"^(?:anomaly\s*[-–—:]\s*|site\s*:\s*)", "", name, flags=re.IGNORECASE)
    return clean.strip()


def parse_with_gemini(html_content):
    """Analyse structurée avec gestion de charge (retry + fallback de modèles)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = """
Tu es un extracteur d'informations expert pour le jeu Ingress Anomaly.
Analyse le code HTML brut officiel de Niantic et extrais avec précision les points de saison (Season Points).

Retourne UNIQUEMENT un objet JSON valide qui respecte exactement cette structure :
{
  "season_overview": [
    {"name": "Nom de l'épreuve/ville (ex: Singapore, Paris, Seoul, Bogotá, Helsinki, Denver, Global Op, First Saturday)", "enl": "score ou ??", "res": "score ou ??"}
  ],
  "sites": [
    {
      "name": "Nom de la ville principale (ex: Singapore, Paris, Seoul, Bogotá, Helsinki, Denver)",
      "enl_pts": "score total du site ou ??",
      "res_pts": "score total du site ou ??",
      "special_ops": {"enl": "score ou 0.0", "res": "score ou 0.0"},
      "shards": {"enl": "score ou ??", "res": "score ou ??"},
      "beacons": {"enl": "score ou ??", "res": "score ou ??"},
      "uniques": {"enl": "score ou ??", "res": "score ou ??"}
    }
  ]
}

Consignes strictes :
- N'extrais JAMAIS les AP ou battle points bruts (ex: 37,287,327). Prends EXCLUSIVEMENT les Season Points (ex: 981.4 / 1018.6).
- Si une épreuve est marquée (Cancelled), les points valent 0.0.
- Si une ville ou une épreuve n'est pas encore complétée (?? ou TBD), indique "??" sans inventer de valeur.
- Dans "sites", ne mets que les villes majeures, pas les doublons.
"""

        # Modèles testés en cascade si surcharge 503
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']

        for model_name in models_to_try:
            for attempt in range(2):  # 2 essais par modèle
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[prompt, html_content],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    return json.loads(response.text)
                except Exception as err:
                    if "503" in str(err) or "UNAVAILABLE" in str(err):
                        print(f"Modèle {model_name} saturé (tentative {attempt + 1}/2). Pause de 4s...")
                        time.sleep(4)
                    else:
                        raise err

        return None
    except Exception as e:
        print(f"Extraction IA non disponible (repli sur analyse classique) : {e}")
        return None

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
                title_text = clean_text(a)

                is_results = bool(re.search(r"-results/?$", href)) or bool(re.search(r"anomaly\s+season\s*-\s*results", title_text, re.IGNORECASE))
                is_overview = bool(re.search(r"anomaly\s+season\s*-\s*overview", title_text, re.IGNORECASE)) or bool(re.search(r"-overview/?$", href))

                if not (is_results or is_overview):
                    continue

                match_slug = re.search(r"/news/(\d{4}-[\w-]+?)(?:-(?:results|overview))?/?$", href)
                if not match_slug:
                    continue

                slug = match_slug.group(1).replace("-results", "").replace("-overview", "")
                if any(bad in slug.lower() for bad in ["anomalysites", "schedule", "rules", "guidelines"]):
                    continue

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
            print(f"Erreur sur la page {page} : {e}")
            break

    modern_known = {
        "2026-cygnus": ("Cygnus (2026)", "https://ingress.com/news/2026-cygnus", "upcoming"),
        "2026-apollo": ("Apollo (2026)", "https://ingress.com/news/2026-apollo-results", "active"),
        "2026-orion": ("Orion (2026)", "https://ingress.com/news/2026-orion-results", "archived"),
        "2026-plusgamma": ("+Gamma (2026)", "https://ingress.com/news/2026-plusgamma-results", "archived")
    }

    for k_slug, (k_title, k_url, k_status) in modern_known.items():
        if k_slug not in discovered:
            discovered[k_slug] = {
                "title": {"fr": k_title, "en": k_title},
                "url": k_url,
                "status": k_status
            }

    for h_slug, h_data in HISTORICAL_SEASONS.items():
        discovered[h_slug] = h_data

    return discovered


def fetch_raw_data(url, status, slug):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    banner = "https://placehold.co/600x300/141c2e/FFF?text=Anomaly"

    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        html_text = res.text
        soup = BeautifulSoup(html_text, "html.parser")

        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_image and og_image.get("content"):
            banner = og_image["content"].strip()
            if banner.startswith("/"):
                banner = f"https://ingress.com{banner}"
    except Exception as e:
        print(f"Erreur de chargement pour {slug} ({url}) : {e}")
        html_text = ""
        soup = BeautifulSoup("", "html.parser")

    if slug in HISTORICAL_SEASONS:
        hist = HISTORICAL_SEASONS[slug]
        return {
            "banner": banner,
            "season_overview": hist["season_overview"],
            "sites": [],
            "has_pending_scores": False,
            "is_upcoming": False,
            "preset_totals": (hist["enl_total"], hist["res_total"])
        }

    if status == "upcoming":
        return {
            "banner": banner,
            "season_overview": [],
            "sites": [],
            "has_pending_scores": False,
            "is_upcoming": True
        }

    # Tentative d'analyse avec l'IA pour la saison en cours (Apollo)
    if slug == "2026-apollo" and os.getenv("GEMINI_API_KEY"):
        print("Analyse IA en cours avec Gemini...")
        ai_result = parse_with_gemini(html_text)
        if ai_result and "season_overview" in ai_result and ai_result["season_overview"]:
            print("Extraction IA validée avec succès !")
            has_pending = any(item["enl"] == "??" or item["res"] == "??" for item in ai_result["season_overview"])
            return {
                "banner": banner,
                "season_overview": ai_result["season_overview"],
                "sites": ai_result.get("sites", []),
                "has_pending_scores": has_pending,
                "is_upcoming": False
            }

    # Analyse de secours par scraping BeautifulSoup
    season_overview_raw = []
    has_pending_scores = False

    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue
        headers_text = [clean_text(th).lower() for th in header_row.find_all(["th", "td"])]

        if len(headers_text) >= 3 and "site" in headers_text[0] and "enlightened" in headers_text[1] and "resistance" in headers_text[2]:
            for r in table.find_all("tr")[1:]:
                cols = [clean_text(td) for td in r.find_all(["td", "th"])]
                if len(cols) >= 3:
                    name_raw = cols[0].strip()
                    if name_raw.lower() in ["season points", "total", ""]:
                        continue
                    enl_v = cols[1].strip()
                    res_v = cols[2].strip()
                    if enl_v in ["??", "TBD", "-"] or res_v in ["??", "TBD", "-"]:
                        enl_v = "??"
                        res_v = "??"
                        has_pending_scores = True

                    norm_name = normalize_city_name(name_raw)
                    if not any(normalize_city_name(item["name"]).lower() == norm_name.lower() for item in season_overview_raw):
                        season_overview_raw.append({
                            "name": name_raw,
                            "enl": enl_v,
                            "res": res_v
                        })

        elif len(headers_text) >= 3 and ("event" in headers_text[0] or "events" in headers_text[0]):
            for r in table.find_all("tr")[1:]:
                cols = [clean_text(td) for td in r.find_all(["td", "th"])]
                if len(cols) >= 3:
                    row_name = cols[0].strip()
                    if any(k in row_name.lower() for k in ["total", "season points total"]):
                        event_title = "Global Op" if "global op" in row_name.lower() else ("First Saturday" if "first saturday" in row_name.lower() else row_name)
                        enl_v = cols[1].replace(",", "").strip()
                        res_v = cols[2].replace(",", "").strip()
                        if not any(item["name"].lower() == event_title.lower() for item in season_overview_raw):
                            season_overview_raw.append({
                                "name": event_title,
                                "enl": enl_v,
                                "res": res_v
                            })

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
            "special_ops": {"enl": "0.0", "res": "0.0"},
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
        while curr:
            if hasattr(curr, "name") and curr.name in ["h2", "h3", "h1"]:
                break

            if hasattr(curr, "get_text"):
                txt = curr.get_text().strip().lower()
                if "special ops" in txt:
                    current_context = "special_ops"
                elif "shard battle" in txt:
                    current_context = "shard"
                elif "beacon battle" in txt:
                    current_context = "beacon"

            if hasattr(curr, "name") and curr.name == "table":
                rows = curr.find_all("tr")
                t_head = rows[0].get_text().lower() if rows else ""
                if "ops" in t_head or "stealth ops" in t_head:
                    current_context = "special_ops"
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
                            if current_context == "special_ops":
                                site_dict["special_ops"] = {"enl": val_e, "res": val_r}
                            elif current_context == "beacon":
                                site_dict["beacons"] = {"enl": val_e, "res": val_r}
                            elif current_context == "unique":
                                site_dict["uniques"] = {"enl": val_e, "res": val_r}

                if current_context == "unique":
                    current_context = ""

            curr = curr.next_sibling

        if site_dict["enl_pts"] == "??" or site_dict["res_pts"] == "??":
            try:
                tot_e = float(site_dict["special_ops"]["enl"]) + float(site_dict["shards"]["enl"]) + float(site_dict["beacons"]["enl"]) + float(site_dict["uniques"]["enl"])
                tot_r = float(site_dict["special_ops"]["res"]) + float(site_dict["shards"]["res"]) + float(site_dict["beacons"]["res"]) + float(site_dict["uniques"]["res"])
                site_dict["enl_pts"] = str(round(tot_e, 1))
                site_dict["res_pts"] = str(round(tot_r, 1))
            except ValueError:
                has_pending_scores = True

        sites_raw.append(site_dict)

    return {
        "banner": banner,
        "season_overview": season_overview_raw,
        "sites": sites_raw,
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
    preset = raw_data.get("preset_totals")
    if preset:
        enl_sum, res_sum = preset
        for row in raw_data["season_overview"]:
            season_overview.append({
                "name": row["name"],
                "enl": row["enl"],
                "res": row["res"],
                "winner": "—"
            })
    else:
        enl_sum = 0.0
        res_sum = 0.0
        for row in raw_data["season_overview"]:
            enl_val = row["enl"]
            res_val = row["res"]
            winner = "—"

            if enl_val != "??" and res_val != "??":
                try:
                    e = float(enl_val.replace(",", "").replace(" ", ""))
                    r = float(res_val.replace(",", "").replace(" ", ""))
                    enl_sum += e
                    res_sum += r
                    winner = "🟢 ENL" if e > r else ("🔵 RES" if r > e else t["tie"])
                except ValueError:
                    pass
            else:
                winner = t["waiting"]

            season_overview.append({
                "name": row["name"],
                "enl": enl_val,
                "res": res_val,
                "winner": winner
            })

    enl_sum = round(enl_sum, 1)
    res_sum = round(res_sum, 1)
    diff = round(res_sum - enl_sum, 1)

    if diff > 0:
        global_status = t["global_res_lead"].format(res=res_sum, enl=enl_sum, diff=diff)
        lead_badge = f"{t['res_lead']} (+{diff})"
        badge_class = "badge-res"
    elif diff < 0:
        global_status = t["global_enl_lead"].format(res=res_sum, enl=enl_sum, diff=round(-diff, 1))
        lead_badge = f"{t['enl_lead']} (+{round(-diff, 1)})"
        badge_class = "badge-enl"
    else:
        global_status = t["global_tie"].format(enl=enl_sum)
        lead_badge = t["tie"]
        badge_class = ""

    tmpl_md = env.get_template("template.md.j2")
    rendered_md = tmpl_md.render(
        t=t,
        season_title=title,
        updated_at=now_iso,
        global_status=global_status,
        enl_total=enl_sum,
        res_total=res_sum,
        diff=diff,
        season_overview=season_overview,
        sites=raw_data["sites"]
    )

    with open(os.path.join(target_dir, f"{slug}.md"), "w", encoding="utf-8") as f:
        f.write(rendered_md)

    html_content = markdown.markdown(rendered_md, extensions=["tables"])
    tmpl_detail = env.get_template("detail_template.html.j2")
    rendered_html = tmpl_detail.render(
        title=title,
        content=html_content,
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

    # Détermination de la saison en cours (Apollo 2026)
    active_slug = None
    for s_slug in ["2026-apollo", "2026-orion", "2026-plusgamma"]:
        if s_slug in scraped_data and scraped_data[s_slug].get("has_pending_scores"):
            active_slug = s_slug
            break

    if active_slug is None and "2026-apollo" in scraped_data:
        active_slug = "2026-apollo"

    # Ordre chronologique strict du plus récent au plus ancien
    SEASON_CHRONO = [
        "2026-cygnus",
        "2026-apollo",
        "2026-orion",
        "2026-plusgamma",
        "2025-plusbeta",
        "2025-plusdelta",
        "2023-discoverie",
        "2023-ctrl",
        "2023-echo",
        "2022-epiphany-dawn",
        "2022-kythera"
    ]

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
            slug = card["slug"]
            chrono_idx = SEASON_CHRONO.index(slug) if slug in SEASON_CHRONO else 99
            return (state_prio, chrono_idx)

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
