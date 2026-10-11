#!/usr/bin/env python3
"""Actualiza el catálogo de la tienda.
Uso:
  update.py daily    -> refresca estrellas/descripción de lo existente
  update.py weekly   -> además busca herramientas nuevas por categoría
"""
import json, sys, time, urllib.request
from datetime import date

BASE = "/home/hatch/workspace/ai-tools-store"
CATALOG = f"{BASE}/data/catalog.json"
SEARCHES = {
    "agentes": "ai agent framework",
    "mcp": "mcp server model context protocol",
    "inferencia": "llm inference serving",
    "voz": "text-to-speech engine",
    "imagen": "stable diffusion webui",
    "rag": "retrieval augmented generation rag",
    "codigo": "ai coding assistant",
}

def gh(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"User-Agent": "wally-store", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    cat = json.load(open(CATALOG))
    today = date.today().isoformat()

    # 1) refrescar existentes
    for t in cat["tools"]:
        try:
            r = gh(f"/repos/{t['name']}")
            t["stars"] = r["stargazers_count"]
            t["lang"] = r["language"]
            t["info_url"] = r["html_url"]
            b = r["default_branch"]
            t["download_url"] = f"https://github.com/{t['name']}/archive/refs/heads/{b}.zip"
            time.sleep(1.2)
        except Exception as e:
            print(f"skip {t['name']}: {e}")

    # 2) descubrimiento semanal
    if mode == "weekly":
        known = {t["name"] for t in cat["tools"]}
        for ckey, q in SEARCHES.items():
            try:
                res = gh(f"/search/repositories?q={urllib.request.quote(q)}&sort=stars&order=desc&per_page=10")
                for item in res.get("items", []):
                    name = item["full_name"]
                    if name in known or item["stargazers_count"] < 500:
                        continue
                    known.add(name)
                    b = item["default_branch"]
                    cat["tools"].append({
                        "name": name,
                        "category": ckey,
                        "category_label": cat["categories"][ckey],
                        "desc": (item["description"] or "Sin descripción.")[:140],
                        "stars": item["stargazers_count"],
                        "lang": item["language"],
                        "info_url": item["html_url"],
                        "download_url": f"https://github.com/{name}/archive/refs/heads/{b}.zip",
                        "first_seen": today,
                    })
                    print(f"nuevo: {name} ({item['stargazers_count']})")
                time.sleep(4)
            except Exception as e:
                print(f"search {ckey}: {e}")

    cat["updated"] = today
    json.dump(cat, open(CATALOG, "w"), ensure_ascii=False, indent=1)
    print(f"catálogo actualizado: {today}, {len(cat['tools'])} herramientas")

if __name__ == "__main__":
    main()
