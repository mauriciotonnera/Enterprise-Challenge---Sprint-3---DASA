import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_JSON = BASE_DIR / "relatorio_genera.json"
CAMINHO_CHROMA = str(BASE_DIR / "chroma_db")
NOME_COLECAO = "relatorio_genera"
MODELO_EMBEDDING = "all-MiniLM-L6-v2"

modelo = SentenceTransformer(MODELO_EMBEDDING)
client = chromadb.PersistentClient(path=CAMINHO_CHROMA)
collection = client.get_or_create_collection(name=NOME_COLECAO)

def carregar_json() -> dict:
    if not CAMINHO_JSON.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {CAMINHO_JSON}")
    with CAMINHO_JSON.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)

def gerar_documentos(dados: dict) -> list[dict]:
    documentos = []

    usuario = dados.get("usuario", {})
    if usuario:
        documentos.append({
            "id": "usuario",
            "texto": f"Dados do usuário do relatório: nome {usuario.get('nome', 'N/A')}, idade {usuario.get('idade', 'N/A')} anos.",
            "tipo": "usuario",
        })

    ancestralidade = dados.get("ancestralidade", {})
    if ancestralidade:
        texto_ancestralidade = "Dados de ancestralidade genética: " + ", ".join([f"{chave}: {valor}%" for chave, valor in ancestralidade.items()])
        documentos.append({"id": "ancestralidade", "texto": texto_ancestralidade, "tipo": "ancestralidade"})

    for i, item in enumerate(dados.get("predisposicoes", [])):
        texto = (
            f"Condição genética avaliada: {item.get('condicao', 'N/A')}. "
            f"Risco informado no relatório: {item.get('risco', 'N/A')}. "
            f"Descrição do relatório: {item.get('descricao', 'N/A')}"
        )
        documentos.append({"id": f"predisposicao_{i}", "texto": texto, "tipo": "predisposicao"})

    return documentos

def indexar() -> None:
    dados = carregar_json()
    documentos = gerar_documentos(dados)
    if not documentos:
        raise ValueError("Nenhum documento foi gerado a partir do JSON.")

    ids = [doc["id"] for doc in documentos]
    textos = [doc["texto"] for doc in documentos]
    metadatas = [{"tipo": doc["tipo"]} for doc in documentos]
    embeddings = modelo.encode(textos).tolist()

    collection.upsert(ids=ids, embeddings=embeddings, documents=textos, metadatas=metadatas)
    print(f"Indexação concluída com sucesso. Total de documentos: {len(documentos)}")

if __name__ == "__main__":
    indexar()
