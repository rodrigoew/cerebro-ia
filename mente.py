"""
Mente: a parte "secretária" do segundo cérebro.

  Organizar pensamentos  você despeja o que está na cabeça; a IA local separa
                         em tarefas, ideias, decisões, lembretes e notas, e você
                         escolhe o que guardar.
  Ideias                 quadro com estados (nova, explorando, em andamento,
                         feita, descartada).
  Decisões               pergunta, opções, prós e contras, critérios, escolha,
                         motivo e data para revisar se deu certo.
  Processos              checklists reutilizáveis ("fechamento do mês",
                         "onboarding de cliente"); cada execução guarda o
                         progresso passo a passo.

Tudo fica no computador. A IA local ajuda a estruturar, mas nunca decide por
você: ela organiza opções e perguntas para você decidir melhor.
"""
from __future__ import annotations

import datetime as dt
import json
import re

ESTADOS_IDEIA = ("nova", "explorando", "em_andamento", "feita", "descartada")


class Mente:
    def __init__(self, memoria, llm, app):
        self.m = memoria
        self.llm = llm
        self.app = app
        with self.m.trava, self.m._con() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS ideias(
              id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, descricao TEXT, estado TEXT NOT NULL DEFAULT 'nova',
              projeto TEXT, criado_em TEXT, atualizado_em TEXT);
            CREATE TABLE IF NOT EXISTS decisoes(
              id INTEGER PRIMARY KEY, pergunta TEXT NOT NULL, contexto TEXT, opcoes TEXT, criterios TEXT,
              perguntas TEXT, escolha TEXT, motivo TEXT, revisar_em TEXT, resultado TEXT,
              estado TEXT NOT NULL DEFAULT 'aberta', criado_em TEXT, atualizado_em TEXT);
            CREATE TABLE IF NOT EXISTS processos(
              id INTEGER PRIMARY KEY, nome TEXT NOT NULL, descricao TEXT, passos TEXT NOT NULL, criado_em TEXT);
            CREATE TABLE IF NOT EXISTS execucoes(
              id INTEGER PRIMARY KEY, processo_id INTEGER, feitos TEXT, iniciado_em TEXT, concluido_em TEXT);
            """)

    def agora(self) -> str:
        return self.app.agora().isoformat()

    def _ia(self) -> bool:
        return self.llm is not None and self.llm.pode_conversar()

    # ------------------------------------------------------------ organizar pensamentos
    def organizar(self, texto: str) -> dict:
        texto = texto.strip()[:6000]
        if not texto:
            raise ValueError("Escreva o que está na sua cabeça.")
        itens = []
        if self._ia():
            try:
                d = self.llm.json([{"role": "user", "content": texto}],
                                  "Você é uma secretária organizada. Separe o texto do usuário em itens curtos e "
                                  "acionáveis, sem inventar nada que não esteja escrito. Responda só com JSON: "
                                  '{"itens": [{"tipo": "tarefa|ideia|decisao|lembrete|nota", "texto": "frase curta", '
                                  '"quando": "data ou prazo citado, ou vazio"}]}', max_tokens=900)
                itens = [{"tipo": str(i.get("tipo", "nota")).replace("decisão", "decisao"),
                          "texto": str(i.get("texto", "")).strip()[:300], "quando": str(i.get("quando", ""))[:60]}
                         for i in d.get("itens", []) if str(i.get("texto", "")).strip()]
            except Exception:
                itens = []
        if not itens:  # sem IA: divide por frases e classifica por regras
            for frase in re.split(r"(?<=[.!?;])\s+|\n+", texto):
                frase = frase.strip(" -•\t")
                if len(frase) < 4:
                    continue
                info = self.m.classificar_nota(frase)
                tipo = {"pendência": "tarefa", "decisão": "decisao", "ideia": "ideia"}.get(info["tipo"], "nota")
                if re.search(r"\b(decidir|escolher|ou nao|ou não|vale a pena)\b", frase, re.I):
                    tipo = "decisao"
                itens.append({"tipo": tipo, "texto": frase[:300], "quando": ""})
        return {"itens": itens[:25]}

    def guardar_itens(self, itens: list[dict]) -> dict:
        from cerebro import interpretar_data
        contagem = {}
        agora_dt = self.app.agora()
        for i in itens[:25]:
            tipo, texto = i.get("tipo"), str(i.get("texto", "")).strip()[:300]
            if not texto:
                continue
            if tipo == "ideia":
                self.criar_ideia(texto)
            elif tipo == "decisao":
                self.criar_decisao(texto, analisar=False)
            elif tipo in ("tarefa", "lembrete"):
                data, hora = interpretar_data(f"{texto} {i.get('quando', '')}", agora_dt)
                self.m.x("INSERT INTO lembretes(texto, data, hora, criado_em) VALUES(?,?,?,?)",
                         (texto, data.isoformat() if data else None, hora.strftime("%H:%M") if hora else None,
                          self.agora()))
            else:
                self.m.salvar_nota(texto, agora_dt)
            contagem[tipo] = contagem.get(tipo, 0) + 1
        return contagem

    # ------------------------------------------------------------ ideias
    def criar_ideia(self, titulo: str, descricao: str = "", projeto: str | None = None) -> int:
        titulo = titulo.strip()[:200]
        if not titulo:
            raise ValueError("Descreva a ideia.")
        if projeto is None:
            projeto = self.m.classificar_nota(titulo).get("projeto")
        return self.m.x("INSERT INTO ideias(titulo, descricao, estado, projeto, criado_em, atualizado_em) "
                        "VALUES(?,?,?,?,?,?)", (titulo, descricao[:2000], "nova", projeto, self.agora(), self.agora()))

    def ideias(self) -> list[dict]:
        return self.m.q("SELECT * FROM ideias ORDER BY atualizado_em DESC LIMIT 300")

    def atualizar_ideia(self, id_: int, dados: dict) -> None:
        campos = {}
        if "estado" in dados:
            if dados["estado"] not in ESTADOS_IDEIA:
                raise ValueError("Estado inválido.")
            campos["estado"] = dados["estado"]
        for k in ("titulo", "descricao", "projeto"):
            if k in dados:
                campos[k] = str(dados[k] or "")[:2000]
        if not campos:
            return
        campos["atualizado_em"] = self.agora()
        self.m.x(f"UPDATE ideias SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?",
                 list(campos.values()) + [id_])

    def apagar_ideia(self, id_: int) -> None:
        self.m.x("DELETE FROM ideias WHERE id = ?", (id_,))

    # ------------------------------------------------------------ decisões
    def criar_decisao(self, pergunta: str, contexto: str = "", analisar: bool = True) -> dict:
        pergunta = pergunta.strip()[:300]
        if not pergunta:
            raise ValueError("Qual é a decisão?")
        analise = self.analisar(pergunta, contexto) if analisar else {"opcoes": [], "criterios": [], "perguntas": []}
        id_ = self.m.x("""INSERT INTO decisoes(pergunta, contexto, opcoes, criterios, perguntas, estado, criado_em, atualizado_em)
                          VALUES(?,?,?,?,?, 'aberta', ?, ?)""",
                       (pergunta, contexto[:3000], json.dumps(analise["opcoes"], ensure_ascii=False),
                        json.dumps(analise["criterios"], ensure_ascii=False),
                        json.dumps(analise["perguntas"], ensure_ascii=False), self.agora(), self.agora()))
        return {"id": id_, **analise}

    def _analise_basica(self, pergunta: str) -> dict:
        base = re.sub(r"(?i)^.*?\b(entre|decidir se|escolher)\b", "", pergunta)
        ops = [o.strip(" ?.") for o in re.split(r"\s+ou\s+|,\s*", base) if 2 < len(o.strip(" ?.")) < 80][:4]
        if len(ops) == 1:
            ops.append("não fazer agora")
        return {"opcoes": [{"nome": o, "pros": [], "contras": []} for o in ops], "criterios": [],
                "perguntas": ["O que acontece se você não decidir agora?", "Qual opção é mais fácil de desfazer?",
                              "Daqui a um ano, qual escolha você teria orgulho de ter feito?"]}

    def analisar(self, pergunta: str, contexto: str = "") -> dict:
        vazio = {"opcoes": [], "criterios": [], "perguntas": []}
        if not self._ia():
            return self._analise_basica(pergunta)
        relevante = self.app.aprendizado.conhecimento_relevante(pergunta, 6) if getattr(self.app, "aprendizado", None) else []
        fatos = "\n".join(f"- {k['texto']}" for k in relevante)
        resultado = self._analise_ia(pergunta, contexto, fatos)
        return resultado if resultado["opcoes"] else self._analise_basica(pergunta)

    def _analise_ia(self, pergunta: str, contexto: str, fatos: str) -> dict:
        vazio = {"opcoes": [], "criterios": [], "perguntas": []}
        try:
            d = self.llm.json([{"role": "user", "content": f"Decisão: {pergunta}\nContexto: {contexto}\n"
                                                          f"O que sei sobre o usuário:\n{fatos}"}],
                              "Ajude o usuário a decidir sem decidir por ele. Liste as opções reais (inclua 'não fazer "
                              "nada' se fizer sentido), prós e contras concretos de cada uma, critérios que importam e "
                              "perguntas que ele deveria responder antes. Use o contexto; não invente fatos. Responda só "
                              'com JSON: {"opcoes": [{"nome": "...", "pros": ["..."], "contras": ["..."]}], '
                              '"criterios": ["..."], "perguntas": ["..."]}', max_tokens=900)
            return {"opcoes": [{"nome": str(o.get("nome", ""))[:100], "pros": [str(x)[:200] for x in o.get("pros", [])][:6],
                                "contras": [str(x)[:200] for x in o.get("contras", [])][:6]}
                               for o in d.get("opcoes", []) if o.get("nome")][:6],
                    "criterios": [str(x)[:150] for x in d.get("criterios", [])][:8],
                    "perguntas": [str(x)[:200] for x in d.get("perguntas", [])][:6]}
        except Exception:
            return vazio

    def decisoes(self) -> list[dict]:
        linhas = self.m.q("SELECT * FROM decisoes ORDER BY estado = 'aberta' DESC, atualizado_em DESC LIMIT 200")
        for l in linhas:
            for k in ("opcoes", "criterios", "perguntas"):
                l[k] = json.loads(l[k] or "[]")
        return linhas

    def atualizar_decisao(self, id_: int, dados: dict) -> None:
        campos = {}
        for k in ("pergunta", "contexto", "escolha", "motivo", "resultado"):
            if k in dados:
                campos[k] = str(dados[k] or "")[:3000]
        for k in ("opcoes", "criterios", "perguntas"):
            if k in dados:
                campos[k] = json.dumps(dados[k], ensure_ascii=False)[:20000]
        if "revisar_em" in dados:
            if dados["revisar_em"]:
                dt.date.fromisoformat(dados["revisar_em"])
            campos["revisar_em"] = dados["revisar_em"] or None
        if "estado" in dados:
            if dados["estado"] not in ("aberta", "decidida", "revisada"):
                raise ValueError("Estado inválido.")
            campos["estado"] = dados["estado"]
        if dados.get("escolha") and "estado" not in dados:
            campos["estado"] = "decidida"
        if not campos:
            return
        campos["atualizado_em"] = self.agora()
        self.m.x(f"UPDATE decisoes SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?",
                 list(campos.values()) + [id_])
        # a decisão tomada vira conhecimento e lembrete de revisão
        if dados.get("escolha"):
            d = self.m.q("SELECT * FROM decisoes WHERE id = ?", (id_,))[0]
            if getattr(self.app, "aprendizado", None):
                self.app.aprendizado.adicionar_conhecimento(
                    f"Decidiu, em {d['atualizado_em'][:10]}: {d['pergunta']} → {d['escolha']}"
                    + (f" (motivo: {d['motivo']})" if d.get("motivo") else ""), "decisões", "decisao", self.agora(), fixo=True)
            if d.get("revisar_em"):
                self.m.x("INSERT INTO lembretes(texto, data, criado_em) VALUES(?,?,?)",
                         (f"Revisar a decisão: {d['pergunta']} (escolhido: {d['escolha']})", d["revisar_em"], self.agora()))

    def apagar_decisao(self, id_: int) -> None:
        self.m.x("DELETE FROM decisoes WHERE id = ?", (id_,))

    # ------------------------------------------------------------ processos
    def criar_processo(self, nome: str, passos: list[str], descricao: str = "") -> int:
        passos = [p.strip()[:200] for p in passos if p and p.strip()][:40]
        if not nome.strip() or not passos:
            raise ValueError("Dê um nome e pelo menos um passo.")
        return self.m.x("INSERT INTO processos(nome, descricao, passos, criado_em) VALUES(?,?,?,?)",
                        (nome.strip()[:120], descricao[:1000], json.dumps(passos, ensure_ascii=False), self.agora()))

    def sugerir_passos(self, nome: str) -> list[str]:
        if not self._ia():
            return []
        try:
            d = self.llm.json([{"role": "user", "content": f"Processo: {nome}"}],
                              "Sugira de 4 a 10 passos curtos e práticos para esse processo, em português do Brasil. "
                              'Responda só com JSON: {"passos": ["..."]}', max_tokens=400)
            return [str(p)[:200] for p in d.get("passos", [])][:10]
        except Exception:
            return []

    def processos(self) -> list[dict]:
        linhas = self.m.q("SELECT * FROM processos ORDER BY nome")
        for l in linhas:
            l["passos"] = json.loads(l["passos"])
            ultima = self.m.q("SELECT * FROM execucoes WHERE processo_id = ? ORDER BY id DESC LIMIT 1", (l["id"],))
            if ultima:
                u = ultima[0]
                u["feitos"] = json.loads(u["feitos"] or "[]")
                l["execucao"] = u
        return linhas

    def encontrar_processo(self, nome: str) -> dict | None:
        from cerebro import sem_acento
        alvo = sem_acento(nome)
        for p in self.processos():
            if alvo in sem_acento(p["nome"]) or sem_acento(p["nome"]) in alvo:
                return p
        return None

    def iniciar_execucao(self, processo_id: int) -> int:
        aberta = self.m.q("SELECT id FROM execucoes WHERE processo_id = ? AND concluido_em IS NULL", (processo_id,))
        if aberta:
            return aberta[0]["id"]
        return self.m.x("INSERT INTO execucoes(processo_id, feitos, iniciado_em) VALUES(?, '[]', ?)",
                        (processo_id, self.agora()))

    def marcar_passo(self, execucao_id: int, indice: int, feito: bool) -> dict:
        e = self.m.q("SELECT e.*, p.passos FROM execucoes e JOIN processos p ON p.id = e.processo_id WHERE e.id = ?",
                     (execucao_id,))
        if not e:
            raise KeyError("Execução não encontrada.")
        e = e[0]
        feitos = set(json.loads(e["feitos"] or "[]"))
        (feitos.add if feito else feitos.discard)(int(indice))
        total = len(json.loads(e["passos"]))
        concluido = self.agora() if len(feitos) >= total else None
        self.m.x("UPDATE execucoes SET feitos = ?, concluido_em = ? WHERE id = ?",
                 (json.dumps(sorted(feitos)), concluido, execucao_id))
        return {"feitos": sorted(feitos), "total": total, "concluido": bool(concluido)}

    def apagar_processo(self, id_: int) -> None:
        self.m.x("DELETE FROM execucoes WHERE processo_id = ?", (id_,))
        self.m.x("DELETE FROM processos WHERE id = ?", (id_,))
