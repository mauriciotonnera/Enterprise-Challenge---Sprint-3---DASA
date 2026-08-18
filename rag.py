from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_CHROMA = str(BASE_DIR / "chroma_db")
NOME_COLECAO = "relatorio_genera"
MODELO_EMBEDDING = "all-MiniLM-L6-v2"

modelo = SentenceTransformer(MODELO_EMBEDDING)
client = chromadb.PersistentClient(path=CAMINHO_CHROMA)
collection = client.get_or_create_collection(name=NOME_COLECAO)

def buscar_contexto(pergunta: str, quantidade: int = 3) -> dict:
    pergunta = pergunta.strip()
    if not pergunta:
        return {"contexto": "", "fontes": []}

    embedding = modelo.encode(pergunta).tolist()
    resultados = collection.query(query_embeddings=[embedding], n_results=quantidade, include=["documents", "metadatas", "distances"])

    documentos = resultados.get("documents", [[]])[0]
    metadatas = resultados.get("metadatas", [[]])[0]
    distances = resultados.get("distances", [[]])[0]

    fontes = []
    for i, documento in enumerate(documentos):
        fontes.append({
            "trecho": documento,
            "tipo": metadatas[i].get("tipo", "desconhecido") if i < len(metadatas) else "desconhecido",
            "distancia": distances[i] if i < len(distances) else None,
        })

    return {"contexto": "\n\n".join(documentos), "fontes": fontes}
