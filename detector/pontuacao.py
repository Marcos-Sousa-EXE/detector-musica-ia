"""Transforma as pistas numa nota de 0 a 100 (chance de ser IA) com os motivos."""
import re
from .util import normalizar
from .youtube import anos_desde

CAMPOS_CREDITO = r"(composer|producer|author|lyricist|writer|arranger|background vocals?|vocals?|performer|" \
                 r"compositor|composi[cç][aã]o|produtor|produ[cç][aã]o|letra|letrista|vocal \d*|arranjo|mixagem|voz)"
MENCOES_IA = r"\b(suno|udio|riffusion|ia generativa|intelig[eê]ncia artificial|gerad[ao] (com|por) ia|" \
             r"feit[ao] (com|por) ia|ai[- ]generated|made with ai|generated (with|by) ai)\b"


def creditos(descricao, artista):
    """'outros' se há nomes de pessoas além do artista; 'so_artista' se tudo é o próprio artista; None se não há."""
    nomes = []
    for linha in (descricao or "").splitlines():
        dono = re.match(r"\s*℗\s*(?:\d{4}\s*)?(.+)", linha)
        if dono:
            nomes.append(re.sub(r"\b(records?|music|musica|música|produç(?:ões|ao)|digital|ltda|label)\b", "", dono.group(1), flags=re.I).strip())
            continue
        m = re.match(rf"\s*{CAMPOS_CREDITO}\s*[:\-]\s*(.+)", linha, re.I)
        if m:
            nomes += [n.strip() for n in re.split(r"[,/&]| e ", m.group(m.lastindex)) if n.strip()]
    if not nomes:
        return None, []
    outros = [n for n in nomes if normalizar(n) not in (normalizar(artista), "") and normalizar(artista) not in normalizar(n)]
    return ("outros" if outros else "so_artista"), sorted(set(outros))[:4]


def pontuar(d):
    """d: dicionário com tudo que foi coletado. Devolve (nota, veredito, pistas[(emoji, texto)])."""
    pistas, soma = [], 0

    def add(pontos, texto):
        nonlocal soma
        soma += pontos
        pistas.append(("🚩" if pontos > 0 else "✅" if pontos < 0 else "➖", texto))

    yt = d.get("youtube")
    # 1. data de publicação
    if yt is None:
        add(0, "Data, descrição e canal: pendente (falta a chave da API do YouTube)")
    elif yt:
        lancada = re.search(r"Released on:\s*(\d{4}-\d{2}-\d{2})", yt["descricao"])
        data = min(filter(None, [yt["publicado"], lancada.group(1) if lancada else None]))
        if data < "2023-01-01":
            add(-60, f"Lançada em {data[:4]}, antes de existir música cantada feita por IA")
        else:
            add(0, f"Lançada em {data[:7]}")
        if re.search(MENCOES_IA, yt["descricao"], re.I):
            add(40, "A descrição do vídeo menciona IA/Suno/Udio")
        tipo, nomes = creditos(yt["descricao"], d["artista"])
        if tipo == "outros":
            add(-15, "Créditos/titular com nomes de outras pessoas: " + ", ".join(nomes))
        elif tipo == "so_artista":
            add(15, "Créditos e titular (℗) só com o nome do próprio artista (padrão comum em IA)")
        else:
            add(0, "Sem créditos na descrição")
        if not d["canal_topic"] and yt.get("canal_criado"):
            idade = anos_desde(yt["canal_criado"])
            por_ano = yt["videos_canal"] / max(idade or 0, 0.25)
            if idade is not None and idade < 2 and yt["videos_canal"] >= 30:
                add(10, f"Canal criado em {yt['canal_criado'][:7]} e já com {yt['videos_canal']} vídeos")
            elif idade is not None and idade < 4 and por_ano >= 60:
                add(10, f"Canal desde {yt['canal_criado'][:4]} com {yt['videos_canal']} vídeos (~{por_ano:.0f} por ano) — ritmo de produção em série")
            else:
                add(0, f"Canal desde {yt['canal_criado'][:4]}, {yt['videos_canal']} vídeos, {yt['inscritos']} inscritos")

    # 2. aviso de IA da Deezer
    av = d.get("aviso")
    if not d.get("deezer"):
        add(0, "Aviso de IA da Deezer: música não está na Deezer")
    elif av == "faixa":
        add(45, "Deezer marca o álbum desta música como 'Conteúdo gerado por IA'")
    elif av == "artista":
        add(35, "Deezer marca outro álbum deste artista como 'Conteúdo gerado por IA'")
    elif av is False:
        add(-10, "Deezer não mostra aviso de IA")
    else:
        add(0, "Aviso de IA da Deezer: não consegui abrir a página")

    # 3. histórico do artista
    h = d.get("historico")
    if h and h.get("estreia"):
        idade = anos_desde(h["estreia"])
        fonte = d.get("fonte_historico", "")
        txt = f"Artista estreou em {h['estreia'][:7]} ({h['lancamentos']} lançamentos{', ' + str(h['fas']) + ' fãs' if h.get('fas') is not None else ''}, {fonte})"
        if idade < 1.5:
            add(15, txt + " — artista muito novo")
        elif idade >= 3:
            add(-15, txt + " — na ativa há anos")
        else:
            add(0, txt)
        meses = max(idade * 12, 1)
        if h["ult90"] >= 10:
            add(15, f"{h['ult90']} lançamentos nos últimos 90 dias — ritmo de robô")
        elif h["lancamentos"] / meses >= 3 and h["lancamentos"] >= 10:
            add(10, f"Média de {h['lancamentos'] / meses:.1f} lançamentos por mês — ritmo acima do humano")
        else:
            add(0, f"Ritmo de lançamentos normal ({h['ult90']} nos últimos 90 dias)")
    else:
        add(0, "Histórico do artista: não encontrado na Deezer nem na Apple")

    # 4. áudio
    a = d.get("audio")
    if a is None:
        add(0, "Análise do áudio: " + d.get("audio_motivo", "sem prévia na Deezer nem na Apple"))
    else:
        txt = f"Áudio (modelo SONICS, prévia da {d['fonte_previa']}): {a}% de chance de IA"
        add(25 if a >= 45 else 5 if a >= 30 else 0 if a >= 20 else -10, txt)

    # 5. rastro na web
    r = d.get("rastro")
    if r:
        novo = h and h.get("estreia") and anos_desde(h["estreia"]) < 1.5
        add(-5 if novo else -15, "Rastro na web: " + ", ".join(r) + (" (pode ser outro artista com o mesmo nome)" if novo else ""))
    else:
        novo = h and h.get("estreia") and anos_desde(h["estreia"]) < 1.5
        add(5 if novo else 0, "Rastro na web: nada encontrado (letras, cifras, Wikipédia)")
    if d.get("musicbrainz"):
        add(-5, "Cadastro no MusicBrainz")
    else:
        add(0, "Sem cadastro no MusicBrainz")

    nota = max(0, min(100, 50 + soma))
    if nota >= 70:
        veredito = "⚠️ Provável IA"
    elif nota >= 55:
        veredito = "🟡 Suspeita"
    elif nota > 30:
        veredito = "❓ Incerta"
    else:
        veredito = "✅ Provável humana"
    return nota, veredito, pistas
