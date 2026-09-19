import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

URL = "https://ingress.com/news/2026-apollo-results"
OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "recap_anomaly.md")


def clean_text(cell):
    return cell.get_text(strip=True).replace("\xa0", " ")


def fetch_and_parse():
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
    res = requests.get(URL, headers=headers, timeout=15)
    res.raise_for_status()
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
            if len(cols) >= 3 and any(k in cols[0].lower() for k in ["apollo global op", "first saturday", "singapore", "paris", "seoul", "bogotá", "helsinki"]):
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

    env = Environment(loader=FileSystemLoader("."))
    tmpl = env.get_template("template.md.j2")
    rendered = tmpl.render(
        season_title="Apollo (2026)",
        updated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        enl_total=round(enl_sum, 1),
        res_total=round(res_sum, 1),
        diff=round(res_sum - enl_sum, 1),
        season_overview=season_overview,
        sites=sites_data
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"Synthèse actualisée dans {OUTPUT_FILE}")


if __name__ == "__main__":
    fetch_and_parse()