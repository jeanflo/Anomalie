import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
import markdown

SEASONS = {
    "2026-apollo": {
        "title": "Apollo (2026)",
        "url": "https://ingress.com/news/2026-apollo-results"
    }
}

OUTPUT_DIR = "public"


def clean_text(cell):
    return cell.get_text(strip=True).replace("\xa0", " ")


def process_season(slug, info, env):
    url = info["url"]
    title = info["title"]
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}

    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"Erreur sur {slug} : {e}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    # 1. Extraction de la bannière officielle
    og_image = soup.find("meta", property="og:image")
    banner = og_image["content"] if og_image else "https://placehold.co/600x300/141c2e/FFF?text=Anomaly"

    # 2. Parsing des scores
    season_overview = []
    enl_sum = 0.0
    res_sum = 0.0

    tables = soup.find_all("table")
    for tbl in tables:
        rows = tbl.find_all("tr")
        if not rows:
            continue
        for r in rows[1:]:
            cols = [clean_text(td) for td in r.find_all(["td", "th"])]
            if len(cols) >= 3 and any(k in cols[0].lower() for k in ["global op", "first saturday", "singapore", "paris", "seoul", "bogotá", "helsinki", "denver"]):
                name = cols[0]
                enl_val = cols[1]
                res_val = cols[2]

                winner = "—"
                if enl_val != "??" and res_val != "??":
                    try:
                        e_float = float(enl_val.replace(",", "").replace(" ", ""))
                        r_float = float(res_val.replace(",", "").replace(" ", ""))
                        enl_sum += e_float
                        res_sum += r_float
                        winner = "🟢 ENL" if e_float > r_float else ("🔵 RES" if r_float > e_float else "⚪ Égalité")
                    except ValueError:
                        pass
                else:
                    winner = "⏳ En attente"

                season_overview.append({
                    "name": name,
                    "enl": enl_val,
                    "res": res_val,
                    "winner": winner
                })

    # 3. Détail par site
    sites_data = []
    site_headers = soup.find_all(string=re.compile(r"Site:\s*(\w+)", re.IGNORECASE))
    for sh in site_headers:
        site_name = sh.strip().replace("Site:", "").strip()
        parent_container = sh.find_parent(["div", "section"]) or soup
        
        # Récupère le score global du site depuis la vue d'ensemble si présent
        site_overview = next((item for item in season_overview if item["name"].lower() == site_name.lower()), None)
        total_enl = site_overview["enl"] if site_overview else "??"
        total_res = site_overview["res"] if site_overview else "??"

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
            # Sous-scores
            if "stealth ops" in txt and len(c) >= 3:
                site_dict["special_ops"] = {"enl": c[1], "res": c[2]}
            elif "anomaly uniques" in txt and len(c) >= 3:
                site_dict["uniques"] = {"enl": c[1], "res": c[2]}

        sites_data.append(site_dict)

    # 4. Rendu Markdown puis compilation HTML
    tmpl_md = env.get_template("template.md.j2")
    rendered_md = tmpl_md.render(
        season_title=title,
        updated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        enl_total=round(enl_sum, 1),
        res_total=round(res_sum, 1),
        diff=round(res_sum - enl_sum, 1),
        season_overview=season_overview,
        sites=sites_data
    )

    # Écriture du .md
    with open(os.path.join(OUTPUT_DIR, f"{slug}.md"), "w", encoding="utf-8") as f:
        f.write(rendered_md)

    # Écriture du .html pour le web
    html_content = markdown.markdown(rendered_md, extensions=["tables"])
    tmpl_detail = env.get_template("detail_template.html.j2")
    rendered_html = tmpl_detail.render(title=title, content=html_content)

    with open(os.path.join(OUTPUT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(rendered_html)

    return {
        "title": title,
        "slug": slug,
        "banner": banner,
        "html_file": f"{slug}.html",
        "enl": round(enl_sum, 1),
        "res": round(res_sum, 1),
        "diff": round(res_sum - enl_sum, 1)
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    env = Environment(loader=FileSystemLoader("."))

    hub_cards = []
    for slug, info in SEASONS.items():
        data = process_season(slug, info, env)
        if data:
            hub_cards.append(data)

    # Rendu du Hub index.html
    tmpl_hub = env.get_template("hub_template.html.j2")
    rendered_hub = tmpl_hub.render(
        seasons=hub_cards,
        updated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    )

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(rendered_hub)

    print(f"Hub généré avec succès dans {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
