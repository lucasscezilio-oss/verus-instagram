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


def main() -> None:
    if not IG_ID or not TOKEN:
        sys.exit("ERRO: secrets INSTAGRAM_BUSINESS_ID / INSTAGRAM_ACCESS_TOKEN nao definidos.")

    slot = sys.argv[1] if len(sys.argv) > 1 else ""
    if slot not in ("08:00", "15:30"):
        sys.exit(f"ERRO: informe o slot (08:00 ou 15:30). Recebido: {slot!r}")

    hoje = agora_br().strftime("%Y-%m-%d")
    agenda = json.loads(AGENDA.read_text(encoding="utf-8"))
    ja_publicados = carregar_publicados()

    candidatos = [
        i
        for i in agenda
        if i["data"] == hoje and i["horario"] == slot and i["id"] not in ja_publicados
    ]

    if not candidatos:
        print(f"Nada a publicar em {hoje} {slot}. Encerrando sem erro.")
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


if __name__ == "__main__":
    main()
