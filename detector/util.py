import json, re, time, unicodedata, urllib.parse, urllib.request

UA = "detector-musica-ia/1.0 (github.com/Marcos-Sousa-EXE/detector-musica-ia)"


def get(url, timeout=25, tentativas=3):
    """GET simples com algumas tentativas. Devolve (status, texto)."""
    erro = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return e.code, ""
            if e.code == 503:
                time.sleep(3)
            erro = e
        except Exception as e:  # noqa: BLE001
            erro = e
        time.sleep(1.5 * (i + 1))
    raise erro


def get_json(url, **kw):
    status, txt = get(url, **kw)
    return json.loads(txt) if status == 200 and txt else {}


def q(texto):
    return urllib.parse.quote(texto)


def normalizar(texto):
    """minúsculas, sem acento, só letras/números e espaço."""
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def slug(texto):
    return normalizar(texto).replace(" ", "-")


def mesmo_artista(a, b):
    a, b = normalizar(a), normalizar(b)
    return bool(a and b) and (a == b or a in b or b in a)
