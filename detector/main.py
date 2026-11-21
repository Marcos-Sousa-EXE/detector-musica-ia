"""Roda a investigação completa em cada música da playlist e gera o relatório."""
import argparse, json, os, traceback
from datetime import datetime, timezone, timedelta
from . import youtube, deezer, apple, web
from .pontuacao import pontuar

PLAYLIST = os.environ.get("PLAYLIST_URL", "https://music.youtube.com/playlist?list=PLTPAJGrfELdk")
ESTADO = "estado/vistas.json"


def investigar(vid, titulo, canal, aviso_ia):
    artista = canal.replace(" - Topic", "").strip() or titulo.split(" - ")[0]
    d = {"video": vid, "titulo": titulo, "canal": canal, "artista": artista, "canal_topic": canal.endswith(" - Topic")}
    etapas = []

    def etapa(nome, func):
        try:
            func()
        except Exception as e:  # noqa: BLE001
            etapas.append(f"{nome}: erro ({str(e)[:80]})")
            traceback.print_exc()

    etapa("YouTube", lambda: d.update(youtube=youtube.detalhes(vid)))

    def _deezer():
        t = deezer.achar_faixa(artista, titulo)
        d["deezer"] = t
        if not t:
            return
        d["artista"] = t["artist"]["name"]
        d["historico"] = deezer.historico_artista(t["artist"]["id"])
        d["fonte_historico"] = "Deezer"
        if t.get("preview"):
            d["previa"], d["fonte_previa"] = t["preview"], "Deezer"
        if aviso_ia:
            r = aviso_ia.album_tem_aviso(t["album"]["id"])
            if r:
                d["aviso"] = "faixa"
                return
            for alb in d["historico"]["albuns_recentes"]:
                if alb != t["album"]["id"] and aviso_ia.album_tem_aviso(alb):
                    d["aviso"] = "artista"
                    return
            d["aviso"] = r
    etapa("Deezer", _deezer)

    def _apple():
        if d.get("previa") and d.get("historico"):
            return
        t = apple.achar_faixa(d["artista"], titulo)
        if not t:
            return
        if not d.get("previa") and t.get("previewUrl"):
            d["previa"], d["fonte_previa"] = t["previewUrl"], "Apple"
        if not d.get("historico"):
            d["historico"] = apple.historico_artista(t["artistId"])
            d["fonte_historico"] = "Apple"
            if d["artista"] == artista:
                d["artista"] = t["artistName"]
    etapa("Apple", _apple)

    def _audio():
        from . import audio
        if d.get("previa"):
            d["audio"] = audio.chance_ia(d["previa"])
    etapa("Áudio", _audio)
    if d.get("previa") and d.get("audio") is None:
        d["audio_motivo"] = "erro ao analisar a prévia"

    etapa("Web", lambda: d.update(rastro=web.rastro(d["artista"])))
    etapa("MusicBrainz", lambda: d.update(musicbrainz=web.musicbrainz(d["artista"])))

    d["nota"], d["veredito"], d["pistas"] = pontuar(d)
    d["erros"] = etapas
    return d


def mensagem_whatsapp(d):
    linhas = [f"🔍 *{d['titulo']}* — {d['artista']}", f"{d['veredito']} · nota {d['nota']}/100", ""]
    linhas += [f"{e} {t}" for e, t in d["pistas"]]
    if d["erros"]:
        linhas += ["", "⚙️ " + "; ".join(d["erros"])]
    linhas += ["", f"https://music.youtube.com/watch?v={d['video']}"]
    return "\n".join(linhas)


def relatorio(resultados):
    agora = datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    md = [f"# Relatório do detector — {agora}", "", "| # | Música | Artista | Nota | Veredito |", "|---|---|---|---|---|"]
    for i, d in enumerate(resultados, 1):
        md.append(f"| {i} | {d['titulo']} | {d['artista']} | {d['nota']} | {d['veredito']} |")
    md.append("")
    for i, d in enumerate(resultados, 1):
        md += [f"## {i}. {d['titulo']} — {d['artista']}", "", f"**{d['veredito']}** · nota **{d['nota']}/100**", ""]
        md += [f"- {e} {t}" for e, t in d["pistas"]]
        if d["erros"]:
            md.append(f"- ⚙️ Falhas técnicas: {'; '.join(d['erros'])}")
        md += ["", "<details><summary>Mensagem para o WhatsApp</summary>", "", "```", mensagem_whatsapp(d), "```", "</details>", ""]
    return "\n".join(md)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--todas", action="store_true", help="investiga todas as músicas, não só as novas")
    args = p.parse_args()

    vistas = set(json.load(open(ESTADO))) if os.path.exists(ESTADO) else set()
    musicas = youtube.ler_playlist(PLAYLIST)
    alvo = musicas if args.todas else [m for m in musicas if m[0] not in vistas]
    print(f"{len(musicas)} músicas na playlist, {len(alvo)} para investigar")
    if not alvo:
        return

    resultados = []
    try:
        aviso = deezer.AvisoIA().__enter__()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        aviso = None
    try:
        for vid, titulo, canal in alvo:
            d = investigar(vid, titulo, canal, aviso)
            print(f"[{d['nota']:3}] {d['veredito']} — {titulo} ({d['artista']})")
            resultados.append(d)
    finally:
        if aviso:
            aviso.__exit__(None, None, None)

    texto = relatorio(resultados)
    os.makedirs("relatorios", exist_ok=True)
    open("relatorios/ultimo.md", "w").write(texto)
    with open("relatorios/ultimo.json", "w") as f:
        json.dump([{k: v for k, v in d.items() if k not in ("deezer", "youtube")} for d in resultados], f, ensure_ascii=False, indent=1)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(texto)
    os.makedirs("estado", exist_ok=True)
    json.dump(sorted(vistas | {d["video"] for d in resultados}), open(ESTADO, "w"), indent=0)


if __name__ == "__main__":
    main()
