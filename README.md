# Detector de músicas feitas por IA

Acompanha uma playlist do YouTube Music compartilhada entre amigos e, a cada música nova, faz uma
investigação completa para estimar se ela foi gerada por inteligência artificial. Cada música recebe
uma nota de 0 a 100 e a lista de motivos — inclusive as pistas que não deram resultado.

## Como funciona

A cada 10 minutos o GitHub Actions confere se entrou música nova. Se entrou, toda música passa por **todas** as pistas:

| Pista | Fonte | Peso |
|---|---|---|
| Data de lançamento (antes de 2023 = humana) | YouTube Data API | decisivo |
| Menção a IA/Suno/Udio na descrição | YouTube Data API | forte |
| Aviso "Conteúdo gerado por IA" no álbum | Deezer (página aberta num navegador) | forte |
| Idade do artista e ritmo de lançamentos | API pública da Deezer / Apple | médio |
| Análise do áudio (modelo [SONICS](https://github.com/awsaf49/sonics)) | Prévia pública de 30 s da Deezer ou Apple | médio |
| Créditos e titular (℗) | Descrição do YouTube | médio |
| Ritmo de produção do canal | YouTube Data API | fraco |
| Rastro na web (letras, cifras, Wikipédia) | Letras, Cifra Club, Cifras, OuvirMúsica, Wikipédia | médio |
| Cadastro no MusicBrainz | API do MusicBrainz | fraco |

Nota ≥ 70: ⚠️ provável IA · 55–69: 🟡 suspeita · 31–54: ❓ incerta · ≤ 30: ✅ provável humana.

O último relatório fica em [`relatorios/ultimo.md`](relatorios/ultimo.md).

## Validação

Testado em 15 músicas com gabarito conferido à mão (7 de IA marcadas pela Deezer, 7 humanas e 1 incerta):
o detector chegou ao mesmo veredito em todas.

## Limitações

- O modelo de áudio erra com geradores mais novos que os do treino (ex.: deixou passar The Velvet Sundown); por isso nunca decide sozinho.
- Sem prévia na Deezer/Apple, a pista de áudio fica de fora e a certeza cai.
- Nome de artista igual ao de um grupo real pode gerar "rastro na web" enganoso.

## Configuração

- Segredo `YT_API_KEY`: chave da YouTube Data API v3.
- Variável `PLAYLIST_URL` (opcional): link da playlist.
