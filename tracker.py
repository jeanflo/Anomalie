import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

# Dictionnaire des saisons à surveiller (Slug du fichier : {Titre, URL})
SEASONS = {
    "2026-apollo": {
        "title": "Apollo (2026)",
        "url": "https://ingress.com/news/2026-apollo-results"
    },
    # Tu pourras ajouter les prochaines séries ici au fil de l'eau :
    # "2026-q4-season": {
    #     "title": "Prochaine Saison (2026)",
    #     "url": "https://ingress.com/news/2026-q4-season-results"
    # }
}

OUTPUT_DIR = "output"


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
        print(f"Erreur lors de la récupération de {slug} ({url}) : {e}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")

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

    sites_data = []
    site_headers = soup.find_all(string=re.compile(r"Site:\s*(\w+)", re.IGNORECASE))
    for sh in site_headers:
        site_name = sh.strip().replace("Site:", "").strip()
        parent_container = sh.find_parent(["div", "section"]) or soup

        site_dict = {
            "name": site_name,
            "enl_pts": "??",
            "res_pts": "??",
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
            elif "season points" in txt and len(c) >= 3:
                site_dict["enl_pts"] = c[1]
                site_dict["res_pts"] = c[2]

        sites_data.append(site_dict)

    tmpl = env.get_template("template.md.j2")
    rendered = tmpl.render(
        season_title=title,
        updated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        enl_total=round(enl_sum, 1),
        res_total=round(res_sum, 1),
        diff=round(res_sum - enl_sum, 1),
        season_overview=season_overview,
        sites=sites_data
    )

    out_file = os.path.join(OUTPUT_DIR, f"{slug}.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"Génération terminée : {out_file}")
    return {
        "title": title,
        "slug": slug,
        "file": f"{slug}.md",
        "enl": round(enl_sum, 1),
        "res": round(res_sum, 1)
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    env = Environment(loader=FileSystemLoader("."))

    processed = []
    for slug, info in SEASONS.items():
        res = process_season(slug, info, env)
        if res:
            processed.append(res)

    # Génération d'un index README.md dans output/ pour lister toutes les séries
    index_md = "# 🏆 Archives des Anomalies Ingress\n\n"
    index_md += f"> Mis à jour le {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    index_md += "| Série / Saison | 🟢 Score ENL | 🔵 Score RES | Lien |\n"
    index_md += "| :--- | :---: | :---: | :--- |\n"
    for item in processed:
        index_md += f"| **{item['title']}** | {item['enl']} | {item['res']} | [Consulter le détail]({item['file']}) |\n"

    with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(index_md)


if __name__ == "__main__":
    main()
