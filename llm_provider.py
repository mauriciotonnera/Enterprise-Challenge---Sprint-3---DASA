from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODELO_PADRAO = "claude-haiku-4-5-20251001"
TIMEOUT_SEGUNDOS = 20


def llm_disponivel() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def gerar_texto(system: str, prompt: str, max_tokens: int = 500) -> str | None:
    """Chama a API da Anthropic. Retorna None (nunca lança exceção) se a chave
    não estiver configurada ou se qualquer etapa falhar, para que o chamador
    sempre possa cair no caminho determinístico."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    modelo = os.environ.get("ANTHROPIC_MODEL", MODELO_PADRAO)
    corpo = json.dumps({
        "model": modelo,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    requisicao = urllib.request.Request(
        API_URL,
        data=corpo,
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        blocos = dados.get("content", [])
        texto = "".join(bloco.get("text", "") for bloco in blocos if bloco.get("type") == "text")
        return texto.strip() or None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return None
