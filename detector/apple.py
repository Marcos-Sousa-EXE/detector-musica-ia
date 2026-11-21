"""Apple Music (API pública do iTunes): prévia de 30 s e histórico do artista quando não há Deezer."""
from datetime import datetime, timezone
from .util import get_json, q, mesmo_artista

API = "https://itunes.apple.com"


def achar_faixa(artista, titulo):
    for termo in (f"{artista} {titulo}", titulo):
        for t in get_json(f"{API}/search?country=BR&entity=song&limit=10&term={q(termo)}").get("results", []):
            if mesmo_artista(t.get("artistName", ""), artista) or mesmo_artista(t.get("artistName", ""), titulo.split(" - ")[0]):
                return t
    return None


def historico_artista(artista_id):
    res = get_json(f"{API}/lookup?id={artista_id}&entity=album&limit=200&country=BR").get("results", [])
    datas = sorted(a["releaseDate"][:10] for a in res if a.get("wrapperType") == "collection" and a.get("releaseDate"))
    hoje = datetime.now(timezone.utc)
    ult90 = sum(1 for d in datas if (hoje - datetime.fromisoformat(d).replace(tzinfo=timezone.utc)).days <= 90)
    return {"fas": None, "lancamentos": len(datas), "estreia": datas[0] if datas else None, "ult90": ult90, "albuns_recentes": []}
