"""Leitura da playlist e dos dados de cada vídeo no YouTube."""
import os
from datetime import datetime, timezone
from .util import get_json

API = "https://www.googleapis.com/youtube/v3"


def chave():
    return os.environ.get("YT_API_KEY", "").strip()


def ler_playlist(url_playlist):
    """Lista (video_id, título, canal) da playlist.

    Com chave da API usa o meio oficial; sem chave usa o yt-dlp só para a lista (sem áudio).
    """
    lista_id = url_playlist.split("list=")[1].split("&")[0]
    if chave():
        itens, token = [], ""
        while True:
            d = get_json(f"{API}/playlistItems?part=snippet&maxResults=50&playlistId={lista_id}&key={chave()}&pageToken={token}")
            for it in d.get("items", []):
                sn = it["snippet"]
                itens.append((sn["resourceId"]["videoId"], sn["title"], sn.get("videoOwnerChannelTitle", "")))
            token = d.get("nextPageToken")
            if not token:
                return itens
    import yt_dlp
    with yt_dlp.YoutubeDL({"extract_flat": True, "quiet": True}) as y:
        info = y.extract_info(f"https://www.youtube.com/playlist?list={lista_id}", download=False)
    return [(e["id"], e.get("title") or "", e.get("channel") or e.get("uploader") or "") for e in info["entries"]]


def detalhes(video_id):
    """Data de publicação, descrição e dados do canal. None se não houver chave."""
    if not chave():
        return None
    v = get_json(f"{API}/videos?part=snippet&id={video_id}&key={chave()}").get("items", [])
    if not v:
        return {}
    sn = v[0]["snippet"]
    c = get_json(f"{API}/channels?part=snippet,statistics&id={sn['channelId']}&key={chave()}").get("items", [{}])[0]
    est = c.get("statistics", {})
    return {
        "publicado": sn.get("publishedAt", "")[:10],
        "descricao": sn.get("description", ""),
        "canal": sn.get("channelTitle", ""),
        "canal_criado": c.get("snippet", {}).get("publishedAt", "")[:10],
        "inscritos": int(est.get("subscriberCount", 0) or 0),
        "videos_canal": int(est.get("videoCount", 0) or 0),
    }


def anos_desde(data_iso):
    if not data_iso:
        return None
    d = datetime.fromisoformat(data_iso[:10]).replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - d).days / 365.25
