# GeneraAI — Sprint 3: Experiência do Usuário

Projeto acadêmico para o Challenge Dasa/Genera — Sprint 3 (Experiência do Usuário).
Evolui o protótipo de RAG construído na Sprint 2 para um produto utilizável: um
dashboard com o resumo do perfil genético e os indicadores de risco, um assistente que
personaliza e simplifica suas respostas mantendo fidelidade ao relatório, resumos automáticos
e salvaguardas de comunicação responsável.

**Vídeo de apresentação (não listado):** `[COLOCAR O LINK DO YOUTUBE AQUI]`

## O que mudou desde a Sprint 2

A Sprint 2 garantiu que o sistema *interpretasse* o relatório com precisão (RAG sobre
`relatorio_genera.json`, indexado com ChromaDB + sentence-transformers). A resposta do agente,
porém, era um template fixo — não havia geração real por LLM, nem personalização, nem interface
além de um chat simples.

A Sprint 3 mantém intacto o núcleo de recuperação (`indexador.py` e `rag.py` não mudaram) e
adiciona uma camada de apresentação e personalização:

| Antes (Sprint 2) | Agora (Sprint 3) |
|---|---|
| `agente.py` devolvia sempre o mesmo template | `agente.py` tenta gerar a resposta com um LLM real (Claude) e só usa o template como *fallback* de segurança |
| Uma única resposta, sem opção de tom | Resposta em linguagem simples **ou** técnica, à escolha do usuário (`simplificador.py`) |
| Nada era salvo entre requisições | Histórico de interações e preferências persistidos em SQLite (`persistencia.py`) |
| Sem resumos | Resumo automático do relatório e do histórico de perguntas (`resumos.py`) |
| Guardrails só no texto do prompt | Guardrails também aplicados *depois* da geração, com filtro anti-alarmismo e disclaimer garantido (`safeguards.py`) |
| `static/index.html`: um campo de chat | `static/index.html`: dashboard com abas (Visão geral, Riscos, Assistente, Histórico) |
| CORS com `allow_credentials=True` + `allow_origins=["*"]` (combinação inválida/arriscada) | CORS corrigido para `allow_credentials=False` |

## Arquitetura

```
relatorio_genera.json → indexador.py → ChromaDB (chroma_db/)
                                             │
pergunta do usuário → rag.py (busca semântica) │
                                             ▼
                                        agente.py ──→ llm_provider.py (Claude, se ANTHROPIC_API_KEY existir)
                                             │              │
                                             │         safeguards.py (fail-closed: reprovou? usa o template)
                                             ▼
                                     simplificador.py (linguagem simples, se solicitado)
                                             │
                                             ▼
                                       persistencia.py (SQLite: histórico + perfil)
                                             │
                                             ▼
                                          main.py (FastAPI) → static/ (dashboard)
```

- `indexador.py`, `rag.py` — reaproveitados da Sprint 2, sem alterações.
- `llm_provider.py` — cliente da API da Anthropic (stdlib `urllib`, sem dependência nova). Sem
  `ANTHROPIC_API_KEY` configurada (ou em caso de qualquer erro), retorna `None` e nunca derruba a
  aplicação — todo o resto do sistema foi desenhado para funcionar 100% offline a partir daí.
- `simplificador.py` — simplificação de linguagem: glossário de termos técnicos, heurística de
  legibilidade (palavras por frase) e reescrita via LLM com fallback para o glossário.
- `safeguards.py` — detector de linguagem alarmista + disclaimer obrigatório. Estratégia
  **fail-closed**: texto gerado por LLM que dispare o filtro é descartado, nunca "corrigido" —
  o sistema usa o caminho determinístico, seguro por construção.
- `resumos.py` — resumo automático do relatório e do histórico de interações, com o mesmo padrão
  de fallback.
- `persistencia.py` — SQLite local (`data/app.db`) com o perfil do usuário (nome, idade, nível de
  linguagem preferido) e o histórico de interações com o agente.
- `agente.py` — orquestra tudo acima e implementa a personalização (ver seção própria).
- `main.py` — FastAPI: endpoints `/chat`, `/perfil` (GET/PUT), `/riscos`, `/resumo/relatorio`,
  `/resumo/interacoes`, `/historico`.
- `static/` — dashboard (HTML/CSS/JS puros, sem framework nem build).

Nenhuma dependência nova foi adicionada em `requirements.txt`: o cliente LLM usa `urllib.request`
e a persistência usa `sqlite3`, ambos da biblioteca padrão do Python.

## Personalização das respostas

O agente personaliza a resposta de três formas concretas (evitando prometer "IA mágica" onde não
há): (1) usa o nome salvo no perfil ao se dirigir ao usuário, quando disponível; (2) adapta o
vocabulário conforme o **nível de linguagem** escolhido pelo usuário — simples ou técnico —
salvo no perfil e ajustável a qualquer momento pelo dashboard ou por requisição; (3) a resposta já
é naturalmente específica à pergunta feita, pois é fundamentada apenas nos trechos recuperados via
RAG para aquela pergunta (`rag.buscar_contexto`), nunca no relatório inteiro.

## Simplificação de linguagem (NLP)

`simplificador.py` implementa duas técnicas complementares:

1. **Glossário determinístico** — termos técnicos (ex.: *predisposição genética*, *variante
   genética*, *ancestralidade*) são detectados no texto e recebem uma explicação em linguagem
   simples entre parênteses, na primeira ocorrência.
2. **Heurística de legibilidade** — `calcular_legibilidade()` mede a média de palavras por frase
   para classificar o texto como simples/moderado/complexo, calculada antes e depois da
   simplificação (exposta pela API e usada no dashboard para mostrar a origem da resposta).

Quando há uma chave de API configurada, uma chamada adicional ao LLM tenta uma reescrita mais
natural (mantendo os fatos, sem novas informações); se essa chamada falhar ou for reprovada pelas
salvaguardas, o resultado do glossário é usado sem que o usuário perceba qualquer erro.

## Resumos automáticos

- **Resumo do relatório** (`GET /resumo/relatorio`): parágrafo com ancestralidade e predisposições,
  recalculado a cada chamada a partir do `relatorio_genera.json` atual.
- **Resumo das interações** (`GET /resumo/interacoes`): parágrafo com os temas já perguntados pelo
  usuário, recalculado a cada chamada a partir do histórico salvo em SQLite — reflete sempre o
  estado mais atual, sem necessidade de invalidação de cache.

## Salvaguardas de comunicação (governança)

- Todo texto que chega ao usuário — resposta do chat, resposta simplificada, resumos — passa por
  `safeguards.aplicar_salvaguardas`/`resolver_texto_seguro` antes de ser devolvido pela API.
- **Anti-alarmismo**: um conjunto de padrões (`"você tem"`, `"diagnóstico:"`, `"fatal"`,
  `"incurável"`, `"urgente"`, `"certamente"`, pontos de exclamação repetidos, entre outros) é
  verificado; se algum for encontrado em uma saída gerada por LLM, ela é **descartada** e
  substituída pelo caminho determinístico — nunca reescrita "na tentativa", para não arriscar
  publicar uma versão só parcialmente corrigida.
- **Disclaimer obrigatório**: `aplicar_disclaimer` garante, de forma idempotente (não duplica), que
  toda resposta relacionada a saúde termine com o aviso de que se trata de informação educacional,
  não um diagnóstico, e que recomenda acompanhamento profissional.
- **Interface**: os cards de risco usam uma paleta de cores deliberadamente calma (tons suaves de
  azul/âmbar/terracota), sem vermelho de alerta nem ícones de alarme, para não contradizer
  visualmente o texto não-alarmista.
- O agente segue instruído (prompt + pós-processamento) a nunca emitir diagnóstico definitivo,
  apenas interpretar o que o relatório descreve.

## Persistência

SQLite em `data/app.db` (criado automaticamente na primeira execução): tabela `perfil` (nome,
idade, nível de linguagem preferido) e tabela `interacoes` (pergunta, resposta simplificada,
resposta técnica, fontes recuperadas, método usado — `llm` ou `regras` —, data/hora). O dashboard
lê e grava nesse banco através da API; nada é perdido ao reiniciar o servidor.

## Entrada multimodal

Não implementada nesta entrega — o enunciado marca esse item como opcional. A arquitetura já
isola a geração (`llm_provider.py`) da orquestração (`agente.py`), então um próximo passo natural
seria um endpoint que aceite uma imagem do relatório, extraia texto/gráficos (OCR ou um modelo com
visão) e injete o resultado como mais uma fonte de contexto para o RAG.

## Como executar

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python indexador.py            # popula o ChromaDB a partir do relatório simulado
```

Para respostas geradas por LLM (opcional — sem isso, o sistema usa o modo por regras
automaticamente):

```bash
export ANTHROPIC_API_KEY="sua-chave-aqui"   # Windows (PowerShell): $env:ANTHROPIC_API_KEY="sua-chave-aqui"
```

```bash
uvicorn main:app --reload
```

Abra no navegador: `http://127.0.0.1:8000/static/index.html`

## Perguntas de teste

- Qual minha ancestralidade?
- Tenho risco de intolerância à lactose?
- O relatório fala algo sobre glúten?
- Isso significa que eu tenho uma doença?

Teste também: trocar o nível de linguagem (simples/técnica) antes de perguntar, editar o nome no
perfil e perguntar novamente, e abrir a aba Histórico depois de algumas perguntas para ver o
resumo automático sendo atualizado.

## Observação importante

As respostas são apenas informativas e educacionais. O sistema não substitui avaliação de
médicos, nutricionistas ou geneticistas.
