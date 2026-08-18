from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_DB = BASE_DIR / "data" / "app.db"
CAMINHO_RELATORIO = BASE_DIR / "relatorio_genera.json"


@contextmanager
def _conectar():
    CAMINHO_DB.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(CAMINHO_DB)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def init_db() -> None:
    with _conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS perfil (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nome TEXT,
                idade INTEGER,
                nivel_linguagem TEXT NOT NULL DEFAULT 'leigo'
            )
            """
        )
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS interacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pergunta TEXT NOT NULL,
                resposta TEXT NOT NULL,
                resposta_tecnica TEXT,
                fontes TEXT,
                nivel_linguagem TEXT,
                metodo TEXT,
                criado_em TEXT NOT NULL
            )
            """
        )
    _seed_perfil_inicial()


def _seed_perfil_inicial() -> None:
    with _conectar() as conexao:
        existe = conexao.execute("SELECT 1 FROM perfil WHERE id = 1").fetchone()
        if existe:
            return

        nome, idade = None, None
        if CAMINHO_RELATORIO.exists():
            dados = json.loads(CAMINHO_RELATORIO.read_text(encoding="utf-8"))
            usuario = dados.get("usuario", {})
            nome, idade = usuario.get("nome"), usuario.get("idade")

        conexao.execute(
            "INSERT INTO perfil (id, nome, idade, nivel_linguagem) VALUES (1, ?, ?, 'leigo')",
            (nome, idade),
        )


def obter_perfil() -> dict:
    with _conectar() as conexao:
        linha = conexao.execute("SELECT nome, idade, nivel_linguagem FROM perfil WHERE id = 1").fetchone()
        return dict(linha) if linha else {"nome": None, "idade": None, "nivel_linguagem": "leigo"}


def atualizar_perfil(nome: str | None = None, idade: int | None = None, nivel_linguagem: str | None = None) -> dict:
    atual = obter_perfil()
    novo_nome = nome if nome is not None else atual["nome"]
    nova_idade = idade if idade is not None else atual["idade"]
    novo_nivel = nivel_linguagem if nivel_linguagem is not None else atual["nivel_linguagem"]

    with _conectar() as conexao:
        conexao.execute(
            "UPDATE perfil SET nome = ?, idade = ?, nivel_linguagem = ? WHERE id = 1",
            (novo_nome, nova_idade, novo_nivel),
        )
    return {"nome": novo_nome, "idade": nova_idade, "nivel_linguagem": novo_nivel}


def salvar_interacao(pergunta: str, resposta: str, resposta_tecnica: str, fontes: list, nivel_linguagem: str, metodo: str) -> None:
    with _conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO interacoes (pergunta, resposta, resposta_tecnica, fontes, nivel_linguagem, metodo, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (pergunta, resposta, resposta_tecnica, json.dumps(fontes, ensure_ascii=False), nivel_linguagem, metodo, datetime.now().isoformat(timespec="seconds")),
        )


def listar_historico(limite: int = 20) -> list[dict]:
    with _conectar() as conexao:
        linhas = conexao.execute(
            "SELECT * FROM interacoes ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()

    historico = []
    for linha in linhas:
        item = dict(linha)
        item["fontes"] = json.loads(item["fontes"]) if item["fontes"] else []
        historico.append(item)
    return historico
