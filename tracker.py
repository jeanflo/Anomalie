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
        "city_results": "Résultats par Ville",
        "col_event": "Épreuve / Événement",
        "col_enl": "🟢 Éclairés (ENL)",
        "col_res": "🔵 Résistance (RES)",
        "col_winner": "Vainqueur",
        "col_category": "Catégorie",
        "total_partial": "TOTAL PARTIEL",
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
        "city_results": "City Results",
        "col_event": "Event / Phase",
        "col_enl": "🟢 Enlightened (ENL)",
        "col_res": "🔵 Resistance (RES)",
        "col_winner": "Winner",
        "col_category": "Category",
        "total_partial": "PARTIAL TOTAL",
        "total_site": "Site Total",
        "date_format": "%Y-%m-%d at %H:%M:%S"
    }
}


def clean_text(cell):
    return cell.get_text(strip=True).replace("\xa0", " ")


def discover_anomaly_seasons():
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    discovered = {}

    try:
        res = requests.get(NEWS_URL, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # 1. Recherche des pages de résultats existantes
        for a in soup.find_all("a", href=True):
            href = a["href"]
            match = re.search(r"/news/(\d{4}-[\w-]+-results)", href)
            if match:
                slug = match.group(1).replace("-results", "")
                full_url = href if href.startswith("http") else f"https://ingress.com{href}"
                parts = slug.split("-")
                year = parts[0] if parts[0].isdigit() else ""
                raw_name = " ".join(parts[1:]) if len(parts) > 1 else slug
                clean_name = raw_name.replace("plus", "+").title()
                display_title = f"{clean_name} ({year})" if year else clean_name

                discovered[slug] = {
                    "title": {"fr": display_title, "en": display_title},
                    "url": full_url,
                    "status": "active"
                }

        # 2. Recherche d'annonces de futures saisons (pages de règles sans page de résultats encore créée)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            match_rules = re.search(r"/news/(\d{4}-[\w-]+)-(?:rules|schedule|details)", href)
            if match_rules:
                slug = match_rules.group(1)
                if slug not in discovered:
                    parts = slug.split("-")
                    year = parts[0] if parts[0].isdigit() else ""
                    raw_name = " ".join(parts[1:]) if len(parts) > 1 else slug
                    clean_name = raw_name.replace("plus", "+").title()
                    display_title = f"{clean_name} ({year})" if year else clean_name
                    full_url = href if href.startswith("http") else f"https://ingress.com{href}"

                    discovered[slug] = {
                        "title": {"fr": display_title, "en": display_title},
                        "url": full_url,
                        "status": "upcoming"
                    }
    except Exception as e:
        print(f"Erreur de détection sur {NEWS_URL} : {e}")

    # Fallbacks connus
    fallback_seasons = {
        "2026-apollo": ("Apollo (2026)", "https://ingress.com/news/2026-apollo-results", "active"),
        "2026-orion": ("Orion (2026)", "https://ingress.com/news/2026-orion-results", "archived"),
        "2026-plusgamma": ("+Gamma (2026)", "https://ingress.com/news/2026-plusgamma-results", "archived"),
        "2025-plusbeta": ("+Beta (2025)", "https://ingress.com/news/2025-plusbeta-results", "archived"),
        "2025-plusdelta": ("+Delta (2025)", "https://ingress.com/news/2025-plusdelta-results", "archived")
    }

    for f_slug, (f_title, f_url, f_status) in fallback_seasons.items():
        if f_slug not in discovered:
            discovered[f_slug] = {
                "title": {"fr": f_title, "en": f_title},
                "url": f_url,
                "status": f_status
            }

    return discovered


def fetch_raw_data(url, status):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    og_image = soup.find("meta", property="og:image")
    banner = og_image["content"] if og_image else "https://placehold.co/600x300/141c2e/FFF?text=Anomaly"

    season_overview_raw = []
    has_pending_scores = False

    if status == "upcoming":
        return {
            "banner": banner,
            "season_overview": [],
            "sites": [],
            "has_pending_scores": False,
            "is_upcoming": True
        }

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

    enl_sum = 0.0
    res_sum = 0.0
    season_overview = []

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
            print(f"Traitement : {slug}...")
            data = fetch_raw_data(info["url"], info.get("status", "active"))
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

        # Les saisons "upcoming" et "live" apparaissent en premier dans le Hub
        hub_cards.sort(key=lambda c: 0 if c["card_state"] == "live" else (1 if c["card_state"] == "upcoming" else 2))

        tmpl_hub = env.get_template("hub_template.html.j2")
        rendered_hub = tmpl_hub.render(
            seasons=hub_cards,
            t=t,
            updated_at=now_iso
        )

        with open(os.path.join(dest_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(rendered_hub)

    print("Actualisation du Hub terminée.")


if __name__ == "__main__":
    main()
