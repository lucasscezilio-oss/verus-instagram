# verus-instagram

Publicação automática do feed de [@lucasscez](https://instagram.com/lucasscez) —
Lucas Cezilio, corretor de imóveis em Goiânia (Verus Boutique Imobiliária).

O GitHub Actions dispara duas vezes por dia e publica a peça agendada para
aquele horário. Não depende de nenhum computador ligado.

## Como funciona

```
agenda.json          o que publicar, em que dia e horário
imagens/             as artes, servidas por raw.githubusercontent.com
publicar.py          lê a agenda e publica via Instagram Graph API
publicados.json      registro do que já foi ao ar (trava anti-duplicata)
.github/workflows/   o agendamento
```

Horários: **08:00** (post estático) e **15:30** (carrossel), horário de Brasília.

## Formato da agenda

```json
[
  {
    "id": "post-exemplo-2026-08-12",
    "data": "2026-08-12",
    "horario": "08:00",
    "imagens": ["https://raw.githubusercontent.com/.../imagens/arquivo.jpg"],
    "legenda": "Texto completo da legenda.\n\nCom quebras de linha.\n.\n.\n#hashtags"
  }
]
```

Uma imagem publica post simples; duas ou mais publicam carrossel.

## Por que as imagens ficam aqui

A API do Instagram não aceita upload de arquivo — ela exige uma URL pública e
vai buscar a imagem. Hospedagens temporárias gratuitas se mostraram frágeis:
em 01/08/2026 o litterbox e o catbox saíram do ar ao mesmo tempo e a publicação
da manhã falhou. Servindo do próprio repositório, a URL é permanente e some uma
dependência externa.

É por isso que o repositório é público.

## Trava contra duplicata

Toda peça publicada tem o `id` gravado em `publicados.json`, e o workflow comita
esse arquivo de volta. Se o agendamento disparar duas vezes, ou alguém rodar
manualmente, a peça não sai de novo — já houve carrossel publicado em
duplicidade por falta desse controle.

## Manutenção

O token do Instagram (`INSTAGRAM_ACCESS_TOKEN`, guardado como secret do
repositório) **expira a cada ~60 dias**. Quando vence, o workflow falha e nada
é publicado. Vale um lembrete no calendário para renovar antes disso.

## O que nunca deve entrar aqui

Este repositório é público. Só artes destinadas à publicação e a agenda.
Nada de tokens, `.env`, planilhas ou arquivos de trabalho.
