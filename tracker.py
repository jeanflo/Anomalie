import os
import re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
import markdown

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

# Archives 2022-2023 aux formats spécifiques (Phases / Multipliers / Final Reports)
HISTORICAL_SEASONS = {
    "2023-discoverie": {
        "title": {"fr": "Discoverie (2023)", "en": "Discoverie (2023)"},
        "url": "https://ingress.com/news/discoverie-rules",
        "status": "archived",
        "banner": "https://ingress.com/assets/images/anomalies/discoverie/discoverie-key-art.jpg",
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
        "banner": "https://ingress.com/assets/images/anomalies/ctrl/ctrl-key-art.jpg",
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
        "banner": "https://ingress.com/assets/images/anomalies/echo/echo-key-art.jpg",
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
        "banner": "https://ingress.com/assets/images/anomalies/epiphany-dawn/epiphany-dawn-key-art.jpg",
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
        "banner": "https://ingress.com/assets/images/anomalies/kythera/kythera-key-art.jpg",
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

    # Saisons modernes connues garanties (2024-2026)
    modern_known = {
        "2026-cygnus": ("Cygnus (2026)", "https://ingress.com/news/2026-cygnus", "upcoming"),
        "2026-apollo": ("Apollo (2026)", "https://ingress.com/news/2026-apollo-results", "active"),
        "2026-orion": ("Orion (2026)", "https://ingress.com/news/2026-orion-results", "archived"),
        "2026-plusgamma": ("+Gamma (2026)", "https://ingress.com/news/2026-plusgamma-results", "archived"),
        "2025-plusbeta": ("+Beta (2025)", "https://ingress.com/news/2025-plusbeta-results", "archived"),
        "2025-plusdelta": ("+Delta (2025)", "https://ingress.com/news/2025-plusdelta-results", "archived")
    }

    for k_slug, (k_title, k_url, k_status) in modern_known.items():
        if k_slug not in discovered:
            discovered[k_slug] = {
                "title": {"fr": k_title, "en": k_title},
                "url": k_url,
                "status": k_status
            }

    # Fusion avec les archives historiques (2022-2023)
    for h_slug, h_data in HISTORICAL_SEASONS.items():
        if h_slug not in discovered:
            discovered[h_slug] = h_data

    return discovered


def fetch_raw_data(url, status, slug):
    if slug in HISTORICAL_SEASONS:
        hist = HISTORICAL_SEASONS[slug]
        return {
            "banner": hist["banner"],
            "season_overview": hist["season_overview"],
            "sites": [],
            "has_pending_scores": False,
            "is_upcoming": False,
            "preset_totals": (hist["enl_total"], hist["res_total"])
        }

    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    og_image = soup.find("meta", property="og:image")
    banner = og_image["content"] if og_image else "https://placehold.co/600x300/141c2e/FFF?text=Anomaly"

    if status == "upcoming":
        return {
            "banner": banner,
            "season_overview": [],
            "sites": [],
            "has_pending_scores": False,
            "is_upcoming": True
        }

    season_overview_raw = []
    has_pending_scores = False

    tables = soup.find_all("table")
    if tables:
        summary_table = tables[0]
        rows = summary_table.find_all("tr")
        for r in rows[1:]:
            cols = [clean_text(td) for td in r.find_all(["td", "th"])]
            if len(cols) >= 3:
                name_clean = cols[0].strip().lower()
                if "total" not in name_clean and name_clean not in ["event", "site", "delta", ""]:
                    if cols[1] == "??" or cols[2] == "??":
                        has_pending_scores = True
                    season_overview_raw.append({
                        "name": cols[0],
                        "enl": cols[1],
                        "res": cols[2]
                    })

    sites_raw = []
    site_headers = soup.find_all(string=re.compile(r"Site:\s*(\w+)", re.IGNORECASE))
    for sh in site_headers:
        site_name = sh.strip().replace("Site:", "").strip()
        parent_container = sh.find_parent(["div", "section"]) or soup

        overview_match = next((item for item in season_overview_raw if item["name"].lower() == site_name.lower()), None)
        total_enl = overview_match["enl"] if overview_match else "??"
        total_res = overview_match["res"] if overview_match else "??"

        site_dict = {
            "name": site_name,
            "enl_pts": total_enl,
            "res_pts": total_res,
            "special_ops": {"enl": "0.0", "res": "0.0"},
            "shards": {"enl": "??", "res": "??"},
            "beacons": {"enl": "??", "res": "??"},
            "uniques": {"enl": "??", "res": "??"}
        }

        for row in parent_container.find_all("tr"):
            c = [clean_text(td) for td in row.find_all(["td", "th"])]
            if not c:
                continue
            txt = c[0].lower()
            if "stealth ops" in txt and len(c) >= 3:
                site_dict["special_ops"] = {"enl": c[1], "res": c[2]}
            elif "anomaly uniques" in txt and len(c) >= 3:
                site_dict["uniques"] = {"enl": c[1], "res": c[2]}

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
        slug=slug
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
    active_slug = None

    for slug, info in seasons.items():
        try:
            print(f"Scraping : {slug}...")
            data = fetch_raw_data(info["url"], info.get("status", "active"), slug)
            scraped_data[slug] = data

            if info.get("status") != "upcoming" and active_slug is None and data.get("has_pending_scores"):
                active_slug = slug
        except Exception as e:
            print(f"Erreur sur {slug} : {e}")

    if active_slug is None:
        for s, inf in seasons.items():
            if inf.get("status") != "upcoming":
                active_slug = s
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

        # Ordre d'affichage : UPCOMING (0) -> LIVE (1) -> ARCHIVED triées par date décroissante (2)
        order = {"upcoming": 0, "live": 1, "archived": 2}
        hub_cards.sort(key=lambda c: (
            order.get(c["card_state"], 3),
            -int(c["slug"][:4]) if c["slug"][:4].isdigit() else 0,
            c["slug"]
        ))

        tmpl_hub = env.get_template("hub_template.html.j2")
        rendered_hub = tmpl_hub.render(
            seasons=hub_cards,
            t=t,
            updated_at=now_iso
        )

        with open(os.path.join(dest_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(rendered_hub)

    print("Actualisation du Hub terminée avec succès.")


if __name__ == "__main__":
    main()
