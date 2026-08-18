from __future__ import annotations

import re

DISCLAIMER = (
    "Esta é uma interpretação informativa e educacional baseada no relatório, e não um "
    "diagnóstico médico. Para decisões relacionadas à saúde, converse com um médico, "
    "nutricionista ou geneticista."
)

_MARCADOR_DISCLAIMER = "não um diagnóstico"

PADROES_ALARMISTAS = [
    re.compile(r"\bvocê (tem|vai ter|vai desenvolver|desenvolverá)\b", re.IGNORECASE),
    re.compile(r"\bdiagnóstico\s*:", re.IGNORECASE),
    re.compile(r"\b(fatal|incurável|terminal)\b", re.IGNORECASE),
    re.compile(r"\burgente(mente)?\b", re.IGNORECASE),
    re.compile(r"\bmorr(er|te)\b", re.IGNORECASE),
    re.compile(r"\bcertamente\b", re.IGNORECASE),
    re.compile(r"!{2,}"),
]


def contem_linguagem_alarmista(texto: str) -> bool:
    return any(padrao.search(texto) for padrao in PADROES_ALARMISTAS)


def aplicar_disclaimer(texto: str) -> str:
    if _MARCADOR_DISCLAIMER in texto.lower():
        return texto
    return f"{texto}\n\n{DISCLAIMER}"


def aplicar_salvaguardas(texto: str) -> str | None:
    """Estratégia fail-closed: se o texto (tipicamente vindo do LLM) contiver
    linguagem alarmista, é descartado (None) para que o chamador use o caminho
    determinístico, que já é seguro por construção. Caso contrário, garante o
    disclaimer e devolve o texto."""
    if contem_linguagem_alarmista(texto):
        return None
    return aplicar_disclaimer(texto)


def resolver_texto_seguro(candidato: str | None, texto_fallback: str) -> tuple[str, str]:
    """Ponto único usado por qualquer gerador (agente, simplificador, resumos):
    valida um candidato (normalmente saída de LLM) e, se ele for None ou reprovar
    no filtro de alarmismo, usa texto_fallback (determinístico, seguro por
    construção). Retorna (texto_final, metodo)."""
    if candidato:
        seguro = aplicar_salvaguardas(candidato)
        if seguro is not None:
            return seguro, "llm"
    return aplicar_disclaimer(texto_fallback), "regras"
