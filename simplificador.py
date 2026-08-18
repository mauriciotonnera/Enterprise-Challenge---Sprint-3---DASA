from __future__ import annotations

import re

import llm_provider

GLOSSARIO = {
    "predisposição genética": "uma característica no DNA que pode aumentar um pouco a chance de algo acontecer, sem garantir que vai acontecer",
    "variante genética": "uma pequena diferença encontrada no seu código genético, o DNA",
    "ancestralidade": "de quais regiões do mundo vieram, ao longo de gerações, os seus antepassados",
    "intolerância à lactose": "dificuldade para digerir o açúcar do leite, a lactose",
    "sensibilidade ao glúten": "reação do corpo a uma proteína chamada glúten, presente no trigo, na cevada e no centeio",
    "risco moderado": "uma chance intermediária, segundo os dados analisados",
    "risco baixo": "uma chance pequena, segundo os dados analisados",
    "risco alto": "uma chance maior, segundo os dados analisados",
    "condição genética": "uma característica ligada ao DNA",
}

SYSTEM_PROMPT_SIMPLIFICACAO = (
    "Você é um redator especializado em comunicação de saúde acessível para pacientes leigos. "
    "Reescreva o texto do usuário em português simples e acolhedor, sem jargão técnico não explicado. "
    "Regras obrigatórias: mantenha TODOS os fatos do texto original, não adicione nenhuma informação nova, "
    "não emita diagnóstico, não use tom alarmista, e não substitua avaliação profissional de saúde."
)


def calcular_legibilidade(texto: str) -> dict:
    frases = [f for f in re.split(r"[.!?\n]+", texto) if f.strip()]
    palavras = texto.split()
    n_frases = max(len(frases), 1)
    n_palavras = len(palavras)
    media = n_palavras / n_frases

    if media <= 12:
        nivel = "simples"
    elif media <= 20:
        nivel = "moderado"
    else:
        nivel = "complexo"

    return {
        "palavras": n_palavras,
        "frases": n_frases,
        "media_palavras_por_frase": round(media, 1),
        "nivel": nivel,
    }


def simplificar_regra(texto: str) -> str:
    resultado = texto
    for termo, explicacao in GLOSSARIO.items():
        padrao = re.compile(re.escape(termo), re.IGNORECASE)
        match = padrao.search(resultado)
        if match:
            achado = match.group(0)
            substituicao = f"{achado} ({explicacao})"
            resultado = resultado[:match.start()] + substituicao + resultado[match.end():]
    return resultado


def simplificar(texto: str, nivel_linguagem: str = "leigo") -> dict:
    legibilidade_antes = calcular_legibilidade(texto)

    if nivel_linguagem != "leigo":
        return {
            "texto": texto,
            "metodo": "original",
            "legibilidade_antes": legibilidade_antes,
            "legibilidade_depois": legibilidade_antes,
        }

    texto_llm = llm_provider.gerar_texto(
        SYSTEM_PROMPT_SIMPLIFICACAO,
        f"Texto para reescrever em linguagem simples:\n\n{texto}",
    )

    if texto_llm:
        texto_final, metodo = texto_llm, "llm"
    else:
        texto_final, metodo = simplificar_regra(texto), "regras"

    return {
        "texto": texto_final,
        "metodo": metodo,
        "legibilidade_antes": legibilidade_antes,
        "legibilidade_depois": calcular_legibilidade(texto_final),
    }
