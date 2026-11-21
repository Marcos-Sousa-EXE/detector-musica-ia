"""Verificação leve: há música nova na playlist? (sem instalar nada pesado)."""
import json, os
from .youtube import ler_playlist
from .main import PLAYLIST, ESTADO

vistas = set(json.load(open(ESTADO))) if os.path.exists(ESTADO) else set()
novas = [m for m in ler_playlist(PLAYLIST) if m[0] not in vistas]
print(f"{len(novas)} música(s) nova(s)")
for m in novas:
    print(" -", m[1], "|", m[2])
with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
    f.write(f"novas={len(novas)}\n")
