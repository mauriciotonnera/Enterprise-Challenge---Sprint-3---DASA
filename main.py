from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agente
import persistencia
import resumos
import simplificador

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_RELATORIO = BASE_DIR / "relatorio_genera.json"

persistencia.init_db()

app = FastAPI(title="Assistente IA Genera — Sprint 3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


class PerguntaRequest(BaseModel):
    pergunta: str
    nivel_linguagem: str = "leigo"


class PerfilUpdate(BaseModel):
    nome: Optional[str] = None
    idade: Optional[int] = None
    nivel_linguagem: Optional[str] = None


def _carregar_relatorio() -> dict:
    return json.loads(CAMINHO_RELATORIO.read_text(encoding="utf-8"))


@app.get("/")
def home():
    return {"mensagem": "API GeneraAI (Sprint 3) ativa. Acesse /static/index.html para usar o dashboard."}


@app.post("/chat")
def chat(request: PerguntaRequest):
    resultado = agente.responder(request.pergunta, request.nivel_linguagem)
    return {"pergunta": request.pergunta, **resultado}


@app.get("/perfil")
def obter_perfil():
    perfil = persistencia.obter_perfil()
    dados = _carregar_relatorio()
    return {**perfil, "ancestralidade": dados.get("ancestralidade", {})}


@app.put("/perfil")
def atualizar_perfil(request: PerfilUpdate):
    return persistencia.atualizar_perfil(nome=request.nome, idade=request.idade, nivel_linguagem=request.nivel_linguagem)


@app.get("/riscos")
def listar_riscos():
    dados = _carregar_relatorio()
    riscos = [
        {
            "condicao": item.get("condicao"),
            "risco": item.get("risco"),
            "descricao": item.get("descricao"),
            "descricao_simplificada": simplificador.simplificar_regra(item.get("descricao", "")),
        }
        for item in dados.get("predisposicoes", [])
    ]
    return {"riscos": riscos}


@app.get("/resumo/relatorio")
def resumo_relatorio():
    return resumos.resumir_relatorio(_carregar_relatorio())


@app.get("/resumo/interacoes")
def resumo_interacoes():
    return resumos.resumir_interacoes(persistencia.listar_historico())


@app.get("/historico")
def historico(limite: int = 20):
    return {"historico": persistencia.listar_historico(limite)}
