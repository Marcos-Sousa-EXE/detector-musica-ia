"""Teste: dá para ouvir as músicas da playlist direto do YouTube no GitHub Actions?

Para cada música da playlist:
  1. tenta pegar 30 s de áudio do YouTube (yt-dlp, sem login) — arquivo temporário, apagado logo depois;
  2. pega a prévia de 30 s da Deezer (API pública);
  3. passa as duas fontes no modelo SONICS (trechos de 5 s, média) e compara.
"""
import os, subprocess, tempfile, time, urllib.parse, urllib.request, json, traceback
import numpy as np

PLAYLIST = os.environ.get("PLAYLIST_URL", "https://music.youtube.com/playlist?list=PLTPAJGrfELdk")
SR = 16000

def ler_playlist():
    import yt_dlp
    with yt_dlp.YoutubeDL({"extract_flat": True, "quiet": True}) as y:
        info = y.extract_info(PLAYLIST.replace("music.youtube.com", "www.youtube.com"), download=False)
    return [(e["id"], e.get("title") or "", e.get("channel") or e.get("uploader") or "") for e in info["entries"]]

def decodificar(caminho):
    """Converte qualquer áudio para mono 16 kHz em memória (numpy)."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)

def audio_youtube(vid):
    import yt_dlp
    with tempfile.TemporaryDirectory() as tmp:
        opts = {"format": "bestaudio", "quiet": True, "no_warnings": True,
                "outtmpl": os.path.join(tmp, "a.%(ext)s"),
                "download_ranges": yt_dlp.utils.download_range_func(None, [(45, 75)]),
                "force_keyframes_at_cuts": False}
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([f"https://www.youtube.com/watch?v={vid}"])
        arq = os.path.join(tmp, os.listdir(tmp)[0])
        return decodificar(arq)  # a pasta temporária é apagada ao sair do "with"

def audio_deezer(titulo, canal):
    artista = canal.replace(" - Topic", "")
    q = urllib.parse.quote(f"{artista} {titulo}")
    d = json.load(urllib.request.urlopen(f"https://api.deezer.com/search?q={q}&limit=1", timeout=20))
    if not d.get("data") or not d["data"][0].get("preview"):
        return None, None
    t = d["data"][0]
    with tempfile.TemporaryDirectory() as tmp:
        arq = os.path.join(tmp, "p.mp3")
        urllib.request.urlretrieve(t["preview"], arq)
        return decodificar(arq), f'{t["artist"]["name"]} – {t["title"]}'

_modelos = {}
def sonics(x):
    import torch
    from sonics import HFAudioClassifier
    if not _modelos:
        for nome in ("gamma", "alpha"):
            m = HFAudioClassifier.from_pretrained(f"awsaf49/sonics-spectttra-{nome}-5s")
            m.eval(); _modelos[nome] = m
    n = 5 * SR
    trechos = [x[i:i + n] for i in range(0, len(x) - n + 1, n)]
    if not trechos:
        return None
    lote = torch.tensor(np.stack(trechos))
    notas = []
    with torch.no_grad():
        for m in _modelos.values():
            notas += torch.sigmoid(m(lote)).flatten().tolist()
    return round(100 * float(np.mean(notas)))

def main():
    linhas = ["| Música | Canal | YouTube | IA (áudio YouTube) | IA (prévia Deezer) |", "|---|---|---|---|---|"]
    musicas = ler_playlist()
    print(f"{len(musicas)} músicas na playlist")
    for vid, titulo, canal in musicas:
        yt, nyt, ndz = "—", "—", "—"
        try:
            t0 = time.time(); a = audio_youtube(vid)
            yt = f"✅ {len(a)/SR:.0f}s em {time.time()-t0:.0f}s"
            try: nyt = f"{sonics(a)}%"
            except Exception as e: nyt = f"erro modelo: {str(e)[:60]}"; traceback.print_exc()
        except Exception as e:
            yt = "❌ " + str(e).replace("\n", " ")[:90]
        try:
            d, nome = audio_deezer(titulo, canal)
            if d is not None: ndz = f"{sonics(d)}%"
            else: ndz = "sem prévia"
        except Exception as e:
            ndz = "erro: " + str(e)[:60]
        linha = f"| {titulo} | {canal} | {yt} | {nyt} | {ndz} |"
        print(linha); linhas.append(linha)
    with open(os.environ.get("GITHUB_STEP_SUMMARY", "resumo.md"), "a") as f:
        f.write("## Teste de áudio\n\n" + "\n".join(linhas) + "\n")

if __name__ == "__main__":
    main()
