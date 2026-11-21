"""Rastro do artista na web: páginas de letras/cifras, Wikipédia e MusicBrainz."""
import time
from .util import get, get_json, q, slug, normalizar


def _pagina_do_artista(url, artista):
    try:
        status, html = get(url, tentativas=2)
    except Exception:  # noqa: BLE001
        return False
    return status == 200 and normalizar(artista) in normalizar(html[:20000])


def rastro(artista):
    s = slug(artista)
    achados = []
    if _pagina_do_artista(f"https://www.letras.mus.br/{s}/", artista):
        achados.append("página no Letras.mus.br")
    if _pagina_do_artista(f"https://www.cifraclub.com.br/{s}/", artista):
        achados.append("cifras no Cifra Club")
    if _pagina_do_artista(f"https://www.cifras.com.br/artista/{s}", artista):
        achados.append("cifras no Cifras.com.br")
    if _pagina_do_artista(f"https://www.ouvirmusica.com.br/{s}/", artista):
        achados.append("página no OuvirMúsica")
    wp = get_json(f"https://pt.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=3&srsearch={q(chr(34) + artista + chr(34) + ' música')}")
    for r in wp.get("query", {}).get("search", []):
        if normalizar(r["title"]) == normalizar(artista):
            achados.append("artigo na Wikipédia")
            break
    return achados


def musicbrainz(artista):
    time.sleep(1.5)  # o MusicBrainz aceita no máximo 1 consulta por segundo
    d = get_json(f"https://musicbrainz.org/ws/2/artist?query=artist:%22{q(artista)}%22&fmt=json&limit=3")
    return any(a.get("score", 0) >= 95 and normalizar(a["name"]) == normalizar(artista) for a in d.get("artists", []))
