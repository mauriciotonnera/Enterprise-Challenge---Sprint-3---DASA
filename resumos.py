from __future__ import annotations

import json

import llm_provider
import safeguards

SYSTEM_PROMPT_RESUMO_RELATORIO = (
    "Você resume relatórios genéticos simulados para pacientes leigos, em português, em um "
    "único parágrafo curto, acolhedor e sem jargão técnico não explicado. Use apenas os dados "
    "fornecidos, sem adicionar nenhuma informação nova e sem emitir diagnóstico."
)

SYSTEM_PROMPT_RESUMO_INTERACOES = (
    "Você resume o histórico de perguntas e respostas de um paciente com um assistente de "
    "relatório genético, em português, em um parágrafo curto listando os temas abordados. "
    "Use apenas o conteúdo fornecido, sem adicionar informação nova."
)


def _resumo_relatorio_regra(dados: dict) -> str:
    usuario = dados.get("usuario", {})
    ancestralidade = dados.get("ancestralidade", {})
    predisposicoes = dados.get("predisposicoes", [])

    partes = []
    if usuario.get("nome"):
        partes.append(f"{usuario['nome']}, {usuario.get('idade', 'N/A')} anos.")

    if ancestralidade:
        composicao = ", ".join(f"{valor}% {origem}" for origem, valor in ancestralidade.items())
        partes.append(f"Ancestralidade genética: {composicao}.")

    if predisposicoes:
        itens = "; ".join(f"{p.get('condicao')} (risco {str(p.get('risco', '')).lower()})" for p in predisposicoes)
        partes.append(f"Predisposições avaliadas no relatório: {itens}.")

    return " ".join(partes) or "O relatório ainda não possui dados suficientes para um resumo."


def resumir_relatorio(dados: dict) -> dict:
    texto_regra = _resumo_relatorio_regra(dados)
    candidato = llm_provider.gerar_texto(
        SYSTEM_PROMPT_RESUMO_RELATORIO,
        f"Dados do relatório (JSON):\n{json.dumps(dados, ensure_ascii=False)}",
    )
    texto, metodo = safeguards.resolver_texto_seguro(candidato, texto_regra)
    return {"texto": texto, "metodo": metodo}


def _resumo_interacoes_regra(historico: list[dict]) -> str:
    perguntas = [item["pergunta"] for item in reversed(historico)]
    lista = "; ".join(perguntas[-5:])
    return f"Você já perguntou sobre: {lista}."


def resumir_interacoes(historico: list[dict]) -> dict:
    if not historico:
        return {"texto": "Você ainda não fez nenhuma pergunta ao assistente.", "metodo": "regras"}

    texto_regra = _resumo_interacoes_regra(historico)
    pares = "\n".join(f"P: {item['pergunta']}\nR: {item['resposta']}" for item in reversed(historico))
    candidato = llm_provider.gerar_texto(SYSTEM_PROMPT_RESUMO_INTERACOES, f"Histórico de interações:\n{pares}")
    texto, metodo = safeguards.resolver_texto_seguro(candidato, texto_regra)
    return {"texto": texto, "metodo": metodo}
