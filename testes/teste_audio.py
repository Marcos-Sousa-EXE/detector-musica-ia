"""Teste da pista de áudio.

Para cada música da playlist (lida pelo yt-dlp só para pegar título e canal):
  1. pega a prévia pública de 30 s da Deezer ou, se não houver, da Apple Music;
  2. passa no modelo SONICS (trechos de 5 s, média das versões gamma e alpha).
"""
import os, subprocess, tempfile, urllib.parse, urllib.request, json, traceback
import numpy as np

PLAYLIST = os.environ.get("PLAYLIST_URL", "https://music.youtube.com/playlist?list=PLTPAJGrfELdk")
SR = 16000


def ler_playlist():
    import yt_dlp
    with yt_dlp.YoutubeDL({"extract_flat": True, "quiet": True}) as y:
        info = y.extract_info(PLAYLIST.replace("music.youtube.com", "www.youtube.com"), download=False)
    return [(e["id"], e.get("title") or "", e.get("channel") or e.get("uploader") or "") for e in info["entries"]]


def decodificar(caminho):
    """Converte o áudio para mono 16 kHz em memória (numpy)."""
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def _baixar_previa(url):
    with tempfile.TemporaryDirectory() as tmp:  # apagado ao sair do "with"
        arq = os.path.join(tmp, "p")
        urllib.request.urlretrieve(url, arq)
        return decodificar(arq)


def audio_previa(titulo, canal):
    """Prévia de 30 s: Deezer primeiro, Apple Music se não achar."""
    artista = canal.replace(" - Topic", "")
    q = urllib.parse.quote(f"{artista} {titulo}")
    d = json.load(urllib.request.urlopen(f"https://api.deezer.com/search?q={q}&limit=1", timeout=20))
    if d.get("data") and d["data"][0].get("preview"):
        return _baixar_previa(d["data"][0]["preview"]), "Deezer"
    a = json.load(urllib.request.urlopen(
        f"https://itunes.apple.com/search?country=BR&entity=song&limit=1&term={q}", timeout=20))
    if a.get("results") and a["results"][0].get("previewUrl"):
        return _baixar_previa(a["results"][0]["previewUrl"]), "Apple"
    return None, None


_modelos = {}


def sonics(x):
    import torch
    from sonics import HFAudioClassifier
    if not _modelos:
        for nome in ("gamma", "alpha"):
            m = HFAudioClassifier.from_pretrained(f"awsaf49/sonics-spectttra-{nome}-5s")
            m.eval()
            _modelos[nome] = m
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
    linhas = ["| Música | Canal | Chance de IA (áudio) | Fonte da prévia |", "|---|---|---|---|"]
    musicas = ler_playlist()
    print(f"{len(musicas)} músicas na playlist")
    for vid, titulo, canal in musicas:
        nota, fonte = "—", "nenhuma"
        try:
            d, fonte = audio_previa(titulo, canal)
            if d is None:
                fonte = "nenhuma"
            else:
                nota = f"{sonics(d)}%"
        except Exception as e:
            nota = "erro: " + str(e)[:80]
            traceback.print_exc()
        linha = f"| {titulo} | {canal} | {nota} | {fonte} |"
        print(linha)
        linhas.append(linha)
    with open(os.environ.get("GITHUB_STEP_SUMMARY", "resumo.md"), "a") as f:
        f.write("## Teste de áudio\n\n" + "\n".join(linhas) + "\n")


if __name__ == "__main__":
    main()
