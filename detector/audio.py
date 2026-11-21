"""Análise do áudio com o modelo SONICS sobre a prévia de 30 s (lida e descartada na hora)."""
import os, subprocess, tempfile, urllib.request
import numpy as np

SR = 16000
_modelos = {}


def _carregar():
    if not _modelos:
        from sonics import HFAudioClassifier
        for nome in ("gamma", "alpha"):
            m = HFAudioClassifier.from_pretrained(f"awsaf49/sonics-spectttra-{nome}-5s")
            m.eval()
            _modelos[nome] = m


def _decodificar(url):
    with tempfile.TemporaryDirectory() as tmp:  # apagado ao sair do "with"
        arq = os.path.join(tmp, "previa")
        urllib.request.urlretrieve(url, arq)
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def chance_ia(url_previa):
    """Média (0-100) da chance de IA em trechos de 5 s, nas versões gamma e alpha do SONICS."""
    import torch
    _carregar()
    x = _decodificar(url_previa)
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
