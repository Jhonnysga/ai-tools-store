#!/usr/bin/env python3
"""Actualiza el catálogo de la tienda.
Uso:
  update.py daily    -> refresca estrellas/descripción de lo existente
  update.py weekly   -> además busca herramientas nuevas por categoría

Campos por herramienta:
  mcp: null | "cliente" | "servidor" | "sdk" | "integracion"
  top: true si es la de más estrellas de su categoría (excluye listas awesome)
  license, pushed_at: de la API de GitHub
Historial de estrellas: data/stars-history.json (últimos 30 días por repo).
"""
import json, os, sys, time, urllib.request
from datetime import date, timedelta

BASE = "/home/hatch/workspace/ai-tools-store"
CATALOG = f"{BASE}/data/catalog.json"
HIST = f"{BASE}/data/stars-history.json"
SEARCHES = {
    "agentes": "ai agent framework",
    "inferencia": "llm inference serving",
    "voz": "text-to-speech engine",
    "imagen": "stable diffusion webui",
    "rag": "retrieval augmented generation rag",
    "codigo": "ai coding assistant",
    "codigo:mcp": "mcp server model context protocol",
    "chat": "open-webui",
    "vectores": "vector database",
    "finetuning": "llm fine-tuning",
    "vision": "yolo object detection",
    "musica": "ai music generation",
    "video": "topic:text-to-video",
    "ocr": "topic:ocr",
    "automatizacion": "workflow automation ai",
}

def gh(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"User-Agent": "wally-store", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def mcp_type_for(name, desc):
    """Clasifica el rol MCP de una herramienta por su nombre/descripción."""
    n, d = name.lower(), (desc or "").lower()
    if "mcp" not in n and "mcp" not in d and "model context protocol" not in d:
        return None
    if "sdk" in n:
        return "sdk"
    if "client" in n:
        return "cliente"
    if "server" in n:
        return "servidor"
    if any(k in n for k in ("proxy", "gateway", "toolbox", "registry")):
        return "integracion"
    if any(k in n for k in ("agent", "assistant", "chat", "desktop", "cli", "pilot")):
        return "cliente"
    return "servidor"

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
            lic = r.get("license")
            t["license"] = lic["key"] if lic else None
            t["pushed_at"] = (r.get("pushed_at") or "")[:10] or None
            time.sleep(1.2)
        except Exception as e:
            print(f"skip {t['name']}: {e}")

    # 2) descubrimiento semanal
    if mode == "weekly":
        known = {t["name"] for t in cat["tools"]}
        for ckey, q in SEARCHES.items():
            from_mcp_search = ckey.endswith(":mcp")
            ckey = ckey.split(":")[0]
            try:
                res = gh(f"/search/repositories?q={urllib.request.quote(q)}&sort=stars&order=desc&per_page=10")
                for item in res.get("items", []):
                    name = item["full_name"]
                    if name in known or item["stargazers_count"] < 500:
                        continue
                    known.add(name)
                    b = item["default_branch"]
                    desc = (item["description"] or "Sin descripción.")[:140]
                    mt = mcp_type_for(name, desc)
                    if from_mcp_search and not mt:
                        mt = "servidor"
                    cat["tools"].append({
                        "name": name,
                        "category": ckey,
                        "category_label": cat["categories"][ckey],
                        "desc": desc,
                        "stars": item["stargazers_count"],
                        "lang": item["language"],
                        "info_url": item["html_url"],
                        "download_url": f"https://github.com/{name}/archive/refs/heads/{b}.zip",
                        "first_seen": today,
                        "mcp": mt,
                        "top": False,
                        "license": None,
                        "pushed_at": None,
                    })
                    print(f"nuevo: {name} ({item['stargazers_count']}) mcp={mt}")
                time.sleep(4)
            except Exception as e:
                print(f"search {ckey}: {e}")

    # 3) tops por categoría (excluye listas awesome)
    for ckey in cat["categories"]:
        cands = [t for t in cat["tools"]
                 if t["category"] == ckey and "awesome" not in t["name"].lower()]
        for t in cat["tools"]:
            if t["category"] == ckey:
                t["top"] = False
        if cands:
            max(cands, key=lambda t: t["stars"])["top"] = True

    # 4) historial de estrellas (últimos 30 días)
    hist = json.load(open(HIST)) if os.path.exists(HIST) else {}
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    for t in cat["tools"]:
        h = hist.setdefault(t["name"], {})
        h[today] = t["stars"]
        for d in [k for k in h if k < cutoff]:
            del h[d]
    json.dump(hist, open(HIST, "w"), ensure_ascii=False, indent=1)

    cat["updated"] = today
    json.dump(cat, open(CATALOG, "w"), ensure_ascii=False, indent=1)
    print(f"catálogo actualizado: {today}, {len(cat['tools'])} herramientas")

if __name__ == "__main__":
    main()
