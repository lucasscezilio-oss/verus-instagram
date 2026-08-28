"""
publicar.py — publica no Instagram a peca agendada para agora.

Roda dentro do GitHub Actions, duas vezes por dia (08:00 e 15:30 de Brasilia).
Le a agenda.json, procura a peca cuja data e horario batem com o disparo atual
e publica via Graph API.

Diferenca importante para a versao que rodava no Mac: aqui as imagens ja estao
publicadas neste proprio repositorio (raw.githubusercontent.com), entao nao
existe etapa de upload para hospedagem temporaria. Era justamente essa etapa
que quebrava - litterbox e catbox cairam em producao em 01/08/2026 e o post
da manha nao saiu.

Credenciais vem de variaveis de ambiente (secrets do repositorio), nunca do
codigo.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).parent
AGENDA = RAIZ / "agenda.json"
PUBLICADOS = RAIZ / "publicados.json"

IG_ID = os.environ.get("INSTAGRAM_BUSINESS_ID", "")
TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
BASE = "https://graph.instagram.com/v19.0"

# Aviso no WhatsApp. Opcional: sem os dois secrets, o script roda igual e so nao avisa.
# Usa o CallMeBot porque a WhatsApp Business API oficial exige portfolio empresarial
# aprovado, onboarding que ja falhou uma vez neste projeto. Ver AVISO-WHATSAPP.md.
ZAP_FONE = os.environ.get("WHATSAPP_PHONE", "")
ZAP_CHAVE = os.environ.get("WHATSAPP_APIKEY", "")

# Brasilia é UTC-3 o ano inteiro (horario de verao foi extinto em 2019).
FUSO_BR = timezone(timedelta(hours=-3))


def agora_br() -> datetime:
    return datetime.now(timezone.utc).astimezone(FUSO_BR)


def carregar_publicados() -> set:
    if PUBLICADOS.exists():
        return set(json.loads(PUBLICADOS.read_text(encoding="utf-8")))
    return set()


def marcar_publicado(item_id: str) -> None:
    """Grava o id num arquivo que o workflow comita de volta.

    E a trava contra duplicata: mesmo que o workflow rode duas vezes (retry,
    disparo manual, atraso do agendador), a peca so vai ao ar uma vez. Ja
    houve carrossel publicado em duplicidade por falta desse controle.
    """
    ids = carregar_publicados()
    ids.add(item_id)
    PUBLICADOS.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8")


def criar_container(url_imagem: str, legenda: str = None, item_carrossel: bool = False) -> str:
    dados = {"access_token": TOKEN, "image_url": url_imagem}
    if item_carrossel:
        dados["is_carousel_item"] = "true"
    elif legenda:
        # A legenda so pode ser definida na criacao do container. A API nao
        # aceita definir depois - ja causou post sem legenda em producao.
        dados["caption"] = legenda
    r = requests.post(f"{BASE}/{IG_ID}/media", data=dados, timeout=60)
    resposta = r.json()
    if "id" not in resposta:
        raise RuntimeError(f"Erro ao criar container: {resposta}")
    return resposta["id"]


def criar_carrossel(ids_filhos: list, legenda: str) -> str:
    r = requests.post(
        f"{BASE}/{IG_ID}/media",
        data={
            "access_token": TOKEN,
            "media_type": "CAROUSEL",
            "children": ",".join(ids_filhos),
            "caption": legenda,
        },
        timeout=60,
    )
    resposta = r.json()
    if "id" not in resposta:
        raise RuntimeError(f"Erro ao montar carrossel: {resposta}")
    return resposta["id"]


def esperar_pronto(container_id: str) -> None:
    for _ in range(24):
        r = requests.get(
            f"{BASE}/{container_id}",
            params={"fields": "status_code", "access_token": TOKEN},
            timeout=30,
        )
        status = r.json().get("status_code", "")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container com erro: {r.json()}")
        time.sleep(5)
    raise RuntimeError("Timeout: o Instagram nao terminou de processar a midia")


def publicar(container_id: str) -> str:
    r = requests.post(
        f"{BASE}/{IG_ID}/media_publish",
        data={"access_token": TOKEN, "creation_id": container_id},
        timeout=60,
    )
    resposta = r.json()
    if "id" not in resposta:
        raise RuntimeError(f"Erro ao publicar: {resposta}")
    return resposta["id"]


def avisar(texto: str) -> None:
    """Manda um aviso no WhatsApp. NUNCA derruba a publicacao.

    Regra de ouro deste arquivo: avisar e acessorio, publicar e o essencial. Se o
    servico de aviso estiver fora do ar, com chave errada ou lento, o post ja foi
    e nao pode ser perdido por causa disso. Por isso engole qualquer excecao.
    """
    if not ZAP_FONE or not ZAP_CHAVE:
        print("Aviso de WhatsApp nao configurado, seguindo sem avisar.")
        return
    try:
        requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": ZAP_FONE, "text": texto, "apikey": ZAP_CHAVE},
            timeout=15,
        )
        print("Aviso enviado no WhatsApp.")
    except Exception as e:  # noqa: BLE001
        print(f"Nao consegui avisar no WhatsApp ({e}). Isso nao afeta a publicacao.")


def main() -> None:
    if not IG_ID or not TOKEN:
        sys.exit("ERRO: secrets INSTAGRAM_BUSINESS_ID / INSTAGRAM_ACCESS_TOKEN nao definidos.")

    # Sem argumento, publica a peca de hoje cujo horario ja passou e que ainda
    # nao foi publicada. E assim porque o agendador do GitHub Actions atrasa e
    # as vezes DESCARTA execucoes (aconteceu em 12/08/2026: o disparo das 11:00
    # UTC nem chegou a ser criado). Como o workflow roda vaias vezes ao longo da
    # janela, qualquer execucao que pegue resolve a pendencia - e as demais
    # saem sem fazer nada, porque publicados.json ja tem o id.
    agora = agora_br()
    hoje = agora.strftime("%Y-%m-%d")
    agenda = json.loads(AGENDA.read_text(encoding="utf-8"))
    ja_publicados = carregar_publicados()

    slot_forcado = sys.argv[1] if len(sys.argv) > 1 else None

    candidatos = [
        i
        for i in agenda
        if i["data"] == hoje
        and i["id"] not in ja_publicados
        and (i["horario"] == slot_forcado if slot_forcado else i["horario"] <= agora.strftime("%H:%M"))
    ]
    candidatos.sort(key=lambda i: i["horario"])

    if not candidatos:
        print(f"Nada pendente em {hoje} às {agora.strftime('%H:%M')}. Encerrando sem erro.")
        return

    item = candidatos[0]
    print(f"Publicando: {item['id']} ({len(item['imagens'])} imagem/ns)")

    if len(item["imagens"]) > 1:
        filhos = [criar_container(u, item_carrossel=True) for u in item["imagens"]]
        container = criar_carrossel(filhos, item["legenda"])
    else:
        container = criar_container(item["imagens"][0], legenda=item["legenda"])

    esperar_pronto(container)
    post_id = publicar(container)

    marcar_publicado(item["id"])
    print(f"Publicado com sucesso. Post ID: {post_id}")

    primeira_linha = item["legenda"].split("\n")[0][:90]
    avisor = "carrossel" if len(item["imagens"]) > 1 else "post"
    avisar(
        f"Publicado no Instagram agora.\n\n"
        f"{item['id']}\n"
        f"{avisor} de {len(item['imagens'])} imagem(ns), agendado para {item['horario']}\n\n"
        f"\"{primeira_linha}...\"\n\n"
        f"instagram.com/lucasscez"
    )


if __name__ == "__main__":
    main()
