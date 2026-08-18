from __future__ import annotations

import llm_provider
import persistencia
import safeguards
import simplificador
from rag import buscar_contexto

SYSTEM_PROMPT_AGENTE = (
    "Você é um agente especialista da Genera para interpretação de relatórios genéticos. "
    "Sua função é responder dúvidas sobre ancestralidade, predisposições genéticas, saúde e "
    "bem-estar com base apenas nos dados fornecidos no contexto.\n"
    "Regras obrigatórias:\n"
    "- Use linguagem simples, amigável e acolhedora.\n"
    "- Não use tom alarmista.\n"
    "- Não diga que o usuário terá uma doença.\n"
    "- Explique que predisposição genética não é diagnóstico.\n"
    "- Recomende acompanhamento profissional quando o assunto envolver saúde.\n"
    "- Se a resposta não estiver no contexto, diga que o relatório não traz essa informação.\n"
    "- Não invente dados.\n"
    "- Não substitua médicos, nutricionistas ou geneticistas.\n"
    "- Se o nome do usuário for informado, pode se dirigir a ele(a) pelo nome."
)


def gerar_prompt(pergunta: str, contexto: str, perfil: dict) -> str:
    nome = perfil.get("nome") or "não informado"
    return (
        f"Nome do usuário: {nome}\n\n"
        f"Contexto recuperado do relatório:\n{contexto}\n\n"
        f"Pergunta do usuário:\n{pergunta}\n\n"
        "Resposta:"
    )


def _resposta_template(contexto: str, perfil: dict) -> str:
    nome = perfil.get("nome")
    abertura = f"{nome}, com base" if nome else "Com base"
    return (
        f"{abertura} no relatório analisado, encontrei as seguintes informações:\n\n"
        f"{contexto}\n\n"
        "De forma simples: esses dados indicam uma predisposição ou característica genética "
        "descrita no relatório, mas não representam um diagnóstico definitivo. Fatores como "
        "estilo de vida, ambiente, histórico familiar e avaliação clínica também podem "
        "influenciar a interpretação."
    )


def responder(pergunta: str, nivel_linguagem: str = "leigo") -> dict:
    resultado_busca = buscar_contexto(pergunta)
    contexto = resultado_busca["contexto"]
    fontes = resultado_busca["fontes"]

    if not contexto:
        resposta = "Não encontrei informações no relatório para responder essa pergunta."
        return {
            "resposta": resposta,
            "resposta_tecnica": resposta,
            "fontes": [],
            "metodo": "regras",
            "metodo_simplificacao": "n/a",
        }

    perfil = persistencia.obter_perfil()
    candidato = llm_provider.gerar_texto(SYSTEM_PROMPT_AGENTE, gerar_prompt(pergunta, contexto, perfil))
    resposta_tecnica, metodo = safeguards.resolver_texto_seguro(candidato, _resposta_template(contexto, perfil))

    if nivel_linguagem == "leigo":
        resultado_simpl = simplificador.simplificar(resposta_tecnica, nivel_linguagem)
        if resultado_simpl["metodo"] == "llm":
            resposta_final, metodo_simplificacao = safeguards.resolver_texto_seguro(
                resultado_simpl["texto"], simplificador.simplificar_regra(resposta_tecnica)
            )
        else:
            resposta_final, metodo_simplificacao = resultado_simpl["texto"], "regras"
    else:
        resposta_final, metodo_simplificacao = resposta_tecnica, "tecnico"

    persistencia.salvar_interacao(pergunta, resposta_final, resposta_tecnica, fontes, nivel_linguagem, metodo)

    return {
        "resposta": resposta_final,
        "resposta_tecnica": resposta_tecnica,
        "fontes": fontes,
        "metodo": metodo,
        "metodo_simplificacao": metodo_simplificacao,
    }
