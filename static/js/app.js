const paineis = document.querySelectorAll(".painel");
const abaBotoes = document.querySelectorAll(".aba-botao");

function ativarAba(nomeAba) {
  paineis.forEach((painel) => {
    painel.hidden = painel.id !== `painel-${nomeAba}`;
    painel.classList.toggle("is-ativo", painel.id === `painel-${nomeAba}`);
  });
  abaBotoes.forEach((botao) => {
    const ativa = botao.dataset.aba === nomeAba;
    botao.classList.toggle("is-ativa", ativa);
    botao.setAttribute("aria-selected", String(ativa));
  });
  if (nomeAba === "historico") carregarHistorico();
}

abaBotoes.forEach((botao) => {
  botao.addEventListener("click", () => ativarAba(botao.dataset.aba));
});

function rotuloMetodo(metodo) {
  if (metodo === "llm") return "Gerado por IA (Claude)";
  if (metodo === "regras") return "Gerado por regras (offline)";
  if (metodo === "tecnico") return "Linguagem técnica";
  return metodo || "";
}

async function buscarJSON(url, opcoes) {
  const resposta = await fetch(url, opcoes);
  if (!resposta.ok) throw new Error(`Falha ao chamar ${url}: ${resposta.status}`);
  return resposta.json();
}

async function carregarPerfil() {
  try {
    const perfil = await buscarJSON("/perfil");
    document.getElementById("perfil-nome").textContent = perfil.nome || "Seu perfil genético";
    document.getElementById("perfil-idade").textContent = perfil.idade ? `${perfil.idade} anos` : "";
    document.getElementById("input-nome").value = perfil.nome || "";
    document.getElementById("input-idade").value = perfil.idade || "";
    document.getElementById("input-nivel").value = perfil.nivel_linguagem || "leigo";
    document.getElementById("chat-nivel").value = perfil.nivel_linguagem || "leigo";
    renderizarAncestralidade(perfil.ancestralidade || {});
  } catch (erro) {
    console.error(erro);
  }
}

function renderizarAncestralidade(ancestralidade) {
  const container = document.getElementById("ancestralidade-barras");
  container.innerHTML = "";
  Object.entries(ancestralidade).forEach(([origem, valor]) => {
    const linha = document.createElement("div");
    linha.className = "barra-linha";
    linha.innerHTML = `
      <span class="barra-rotulo">${origem}</span>
      <span class="barra-trilho"><span class="barra-preenchimento" style="width:${valor}%"></span></span>
      <span class="barra-valor">${valor}%</span>
    `;
    container.appendChild(linha);
  });
}

async function carregarResumoRelatorio() {
  const textoEl = document.getElementById("resumo-relatorio-texto");
  const metodoEl = document.getElementById("resumo-relatorio-metodo");
  try {
    const resumo = await buscarJSON("/resumo/relatorio");
    textoEl.textContent = resumo.texto;
    textoEl.classList.remove("texto-carregando");
    metodoEl.textContent = rotuloMetodo(resumo.metodo);
  } catch (erro) {
    textoEl.textContent = "Não foi possível gerar o resumo agora.";
  }
}

function classeRisco(risco) {
  const nivel = (risco || "").toLowerCase();
  if (nivel.includes("alto")) return "alto";
  if (nivel.includes("moder")) return "moderado";
  return "baixo";
}

async function carregarRiscos() {
  const container = document.getElementById("cards-riscos");
  try {
    const { riscos } = await buscarJSON("/riscos");
    container.innerHTML = "";
    riscos.forEach((item) => {
      const card = document.createElement("article");
      card.className = "card-risco";
      card.innerHTML = `
        <span class="badge-risco ${classeRisco(item.risco)}">Risco ${item.risco}</span>
        <h4>${item.condicao}</h4>
        <p>${item.descricao_simplificada}</p>
      `;
      container.appendChild(card);
    });
  } catch (erro) {
    container.innerHTML = "<p>Não foi possível carregar os indicadores agora.</p>";
  }
}

async function carregarHistorico() {
  const listaEl = document.getElementById("lista-historico");
  const resumoTextoEl = document.getElementById("resumo-interacoes-texto");
  const resumoMetodoEl = document.getElementById("resumo-interacoes-metodo");

  try {
    const { historico } = await buscarJSON("/historico");
    listaEl.innerHTML = "";
    if (historico.length === 0) {
      listaEl.innerHTML = "<p class=\"texto-suave\">Nenhuma interação registrada ainda.</p>";
    }
    historico.forEach((item) => {
      const bloco = document.createElement("div");
      bloco.className = "item-historico";
      bloco.innerHTML = `
        <p class="pergunta">${item.pergunta}</p>
        <p class="resposta">${item.resposta}</p>
        <time>${new Date(item.criado_em).toLocaleString("pt-BR")}</time>
      `;
      listaEl.appendChild(bloco);
    });
  } catch (erro) {
    listaEl.innerHTML = "<p>Não foi possível carregar o histórico agora.</p>";
  }

  try {
    const resumo = await buscarJSON("/resumo/interacoes");
    resumoTextoEl.textContent = resumo.texto;
    resumoTextoEl.classList.remove("texto-carregando");
    resumoMetodoEl.textContent = rotuloMetodo(resumo.metodo);
  } catch (erro) {
    resumoTextoEl.textContent = "Não foi possível gerar o resumo agora.";
  }
}

document.getElementById("form-perfil").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const nome = document.getElementById("input-nome").value.trim();
  const idadeValor = document.getElementById("input-idade").value;
  const nivel_linguagem = document.getElementById("input-nivel").value;

  await buscarJSON("/perfil", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nome: nome || null,
      idade: idadeValor ? Number(idadeValor) : null,
      nivel_linguagem,
    }),
  });
  document.getElementById("chat-nivel").value = nivel_linguagem;
  carregarPerfil();
});

const chatEl = document.getElementById("chat");

function adicionarMensagem(texto, classe) {
  const msg = document.createElement("div");
  msg.className = `msg ${classe}`;
  msg.textContent = texto;
  chatEl.appendChild(msg);
  chatEl.scrollTop = chatEl.scrollHeight;
  return msg;
}

document.getElementById("form-chat").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const input = document.getElementById("chat-input");
  const pergunta = input.value.trim();
  if (!pergunta) return;
  const nivel_linguagem = document.getElementById("chat-nivel").value;

  adicionarMensagem(pergunta, "usuario");
  input.value = "";
  const carregando = adicionarMensagem("Consultando o relatório...", "bot");

  try {
    const dados = await buscarJSON("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta, nivel_linguagem }),
    });

    carregando.textContent = dados.resposta;

    const meta = document.createElement("span");
    meta.className = "msg-meta";
    meta.textContent = rotuloMetodo(dados.metodo_simplificacao || dados.metodo);
    carregando.appendChild(meta);

    if (dados.fontes && dados.fontes.length > 0) {
      const detalhes = document.createElement("details");
      const resumoTag = document.createElement("summary");
      resumoTag.textContent = "Ver fontes recuperadas do relatório";
      detalhes.appendChild(resumoTag);
      dados.fontes.forEach((fonte, indice) => {
        const p = document.createElement("p");
        p.textContent = `${indice + 1}. [${fonte.tipo}] ${fonte.trecho}`;
        detalhes.appendChild(p);
      });
      if (dados.resposta_tecnica && dados.resposta_tecnica !== dados.resposta) {
        const tecnica = document.createElement("p");
        tecnica.innerHTML = `<strong>Resposta técnica:</strong> ${dados.resposta_tecnica}`;
        detalhes.appendChild(tecnica);
      }
      carregando.appendChild(detalhes);
    }
  } catch (erro) {
    carregando.textContent = "Não consegui responder agora. Verifique se o backend está rodando.";
  }
});

carregarPerfil();
carregarResumoRelatorio();
carregarRiscos();
