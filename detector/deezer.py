import re
"""Deezer: encontrar a faixa, histórico do artista e o aviso de IA da página do álbum."""
from datetime import datetime, timezone
from .util import get_json, q, mesmo_artista

API = "https://api.deezer.com"


def achar_faixa(artista, titulo):
    """Procura a faixa e só aceita se o artista bater com o canal/título do YouTube."""
    partes = [p.strip() for p in re.split(r"[|\-–]", titulo) if len(p.strip()) > 3]
    tentativas = [f'artist:"{artista}" track:"{titulo}"', f"{artista} {titulo}"] + [f"{artista} {p}" for p in partes] + [titulo]
    for consulta in tentativas:
        if not consulta.strip():
            continue
        for t in get_json(f"{API}/search?q={q(consulta)}&limit=10").get("data", []):
            nome = t["artist"]["name"]
            if mesmo_artista(nome, artista) or mesmo_artista(nome, titulo.split(" - ")[0]):
                return t
    return None


def historico_artista(artista_id):
    ar = get_json(f"{API}/artist/{artista_id}")
    albuns = get_json(f"{API}/artist/{artista_id}/albums?limit=300").get("data", [])
    datas = sorted(a["release_date"] for a in albuns if a.get("release_date"))
    hoje = datetime.now(timezone.utc)
    dias = lambda d: (hoje - datetime.fromisoformat(d).replace(tzinfo=timezone.utc)).days  # noqa: E731
    recentes = sorted(albuns, key=lambda a: a.get("release_date", ""), reverse=True)
    return {
        "fas": ar.get("nb_fan", 0),
        "lancamentos": len(datas),
        "estreia": datas[0] if datas else None,
        "ult90": sum(1 for d in datas if dias(d) <= 90),
        "albuns_recentes": [a["id"] for a in recentes[:3]],
    }


class AvisoIA:
    """Abre a página do álbum num navegador de verdade (Playwright) e procura o aviso de IA."""

    def __init__(self):
        self._pw = self._nav = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._nav = self._pw.chromium.launch()
        self._ctx = self._nav.new_context(locale="pt-BR", viewport={"width": 1280, "height": 900})
        return self

    def __exit__(self, *a):
        if self._nav:
            self._nav.close()
        if self._pw:
            self._pw.stop()

    def album_tem_aviso(self, album_id):
        """True/False; None se a página não carregou direito."""
        pag = self._ctx.new_page()
        try:
            pag.goto(f"https://www.deezer.com/br/album/{album_id}", wait_until="domcontentloaded", timeout=45000)
            try:
                pag.wait_for_selector('[data-testid="ai-generated-alert"]', timeout=12000)
                return True
            except Exception:  # noqa: BLE001
                pass
            # confere se a página do álbum renderizou (lista de faixas) antes de dizer "não tem"
            corpo = pag.inner_text("body")
            return False if ("faixa" in corpo.lower() or "track" in corpo.lower()) else None
        except Exception:  # noqa: BLE001
            return None
        finally:
            pag.close()
