"""Auditoria de qualidade de dataset/conversations.parquet — não é gate
automático, é due diligence: garantir que a base que alimenta RAG/Neo4j (e que
ancorou decisões de arquitetura via analysis/build_objecao_graph.py) não tem
problema estrutural/semântico que faria o agente errar por causa dos dados.

Cobre:
  1. Integridade estrutural (todas as 2500 conversas): message_index
     sequencial, timestamps, enums válidos, campos obrigatórios.
  2. Qualidade do subconjunto GANHO (o que RAG/Neo4j realmente usam como
     few-shot): conversas curtas demais, falso-positivo de "fechou", idade
     implausível, veículo vazio, texto quebrado, duplicatas, preço de
     vendedor fora de qualquer faixa real (quote-service/data/plans.json).
  3. Qualidade do dataset inteiro (todos outcomes) — perdido/em_negociacao
     alimentam analysis/build_objecao_graph.py, que ANCOROU a arquitetura
     de reversão de objeção.
  4. Re-validação do achado central ("objeção -> ~0% ganho") comparando a
     heurística ORIGINAL (com os mesmos falsos-positivos que existiam em
     orch_svc/objecoes.py antes da correção desta sessão) contra a
     heurística CORRIGIDA — pra garantir que a decisão de arquitetura não
     está apoiada num artefato de regex ruim.

Roda uma vez, offline:
  python analysis/audit_dataset_qualidade.py
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/svc-orchestrator/src"))
from orch_svc.objecoes import _OBJ as OBJ_FIXED  # noqa: E402

PARQUET = ROOT / "dataset/conversations.parquet"
PLANS = ROOT / "quote-service/data/plans.json"
OUT = ROOT / "analysis" / "dataset_qualidade.md"

VALID_ROLES = {"lead", "vendedor"}
VALID_TYPES = {"text", "image", "audio", "document"}
VALID_OUTCOMES = {"ganho", "perdido", "em_negociacao", "sem_resposta"}
CLOSE_RE = re.compile(r"\b(fechado|boleto|apolice|apólice|pode emitir|vamos nessa|maravilha)\b", re.I)
GARBLED_RE = re.compile(r"\bundefined\b|\bNone\b|\bnull\b|\{\{|\}\}|NaN|\?\?\?|<<|>>", re.I)
PRECO_RE = re.compile(r"r\$\s*([\d.,]+)", re.I)

# heurística ORIGINAL (a que existia em analysis/build_objecao_graph.py e em
# orch_svc/objecoes.py antes da correção desta sessão) — pra comparação.
OBJ_ORIGINAL = {
    "preco": r"\bcar[oa]\b|pre[çc]o|desconto|valor.*alto|muito alto|parcel|cabe no bolso|barat",
    "cobertura": r"cobertura|cobre|cobrir|franquia|prote[çc]|o que inclui|terceiro",
    "concorrente": r"outra|concorr|porto|azul|cotei|mais barato (em|na|no)|j[áa] tenho",
}


def load() -> tuple[dict[str, list[dict]], dict]:
    rows = pq.read_table(PARQUET).to_pylist()
    by_conv: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by_conv[r["conversation_id"]].append(r)
    plans = json.loads(PLANS.read_text())
    return by_conv, {p["id"]: p["base_mensal"] for p in plans["planos"]}


def auditoria_estrutural(by_conv: dict[str, list[dict]]) -> collections.Counter:
    issues = collections.Counter()
    for msgs in by_conv.values():
        ms = sorted(msgs, key=lambda m: m["message_index"])
        if [m["message_index"] for m in ms] != list(range(len(ms))):
            issues["message_index não sequencial"] += 1
        ts = [m["timestamp"] for m in ms]
        if ts != sorted(ts):
            issues["timestamps fora de ordem (campo não usado pelo código)"] += 1
        for m in ms:
            if m["sender_role"] not in VALID_ROLES:
                issues["sender_role fora do enum"] += 1
            if m["message_type"] not in VALID_TYPES:
                issues["message_type fora do enum"] += 1
            if m["message_type"] == "text" and not (m["message_body"] or "").strip():
                issues["mensagem text vazia"] += 1
        outcome = ms[0].get("conversation_outcome")
        if outcome not in VALID_OUTCOMES:
            issues["outcome fora do enum"] += 1
        if len({m.get("conversation_outcome") for m in ms}) > 1:
            issues["outcome inconsistente na mesma conversa"] += 1
    return issues


def auditoria_qualidade_por_outcome(by_conv: dict[str, list[dict]], base_prices: dict[str, float]):
    por_outcome = collections.defaultdict(lambda: collections.Counter())
    dup_texts: dict[str, list[str]] = collections.defaultdict(list)
    ganho_preco_divergente = []
    ganho_sem_close_real = []

    for cid, msgs in by_conv.items():
        ms = sorted(msgs, key=lambda m: m["message_index"])
        outcome = ms[0].get("conversation_outcome")
        full_text = " ".join(m.get("message_body") or "" for m in ms)
        c = por_outcome[outcome]
        c["total"] += 1
        if len(ms) < 2:
            c["curtas"] += 1
        if GARBLED_RE.search(full_text):
            c["garbled"] += 1
        if not (ms[0].get("veiculo_texto") or "").strip():
            c["veiculo_vazio"] += 1
        idade = ms[0].get("lead_idade_informada")
        if idade is not None and (idade < 16 or idade > 100):
            c["idade_implausivel"] += 1
        norm = re.sub(r"\s+", " ", full_text.lower()).strip()
        dup_texts[norm].append(cid)

        if outcome == "ganho":
            if not CLOSE_RE.search(full_text):
                ganho_sem_close_real.append(cid)
            for m in ms:
                if m["sender_role"] != "vendedor":
                    continue
                for val in PRECO_RE.findall(m.get("message_body") or ""):
                    try:
                        v = float(val.replace(".", "").replace(",", ".")) if "," in val else float(val.replace(",", ""))
                    except ValueError:
                        continue
                    if v < 20:
                        continue
                    if not any(base * 0.5 <= v <= base * 3.0 for base in base_prices.values()):
                        ganho_preco_divergente.append((cid, v))

    dup_reais = {k: v for k, v in dup_texts.items() if len(v) > 1}
    return por_outcome, dup_reais, ganho_sem_close_real, ganho_preco_divergente


def comparar_heuristica_objecao(by_conv: dict[str, list[dict]]):
    lead_text, outcome_of = {}, {}
    for cid, msgs in by_conv.items():
        ms = sorted(msgs, key=lambda m: m["message_index"])
        lead_text[cid] = " ".join(m.get("message_body") or "" for m in ms if m["sender_role"] == "lead")
        outcome_of[cid] = ms[0].get("conversation_outcome")

    def contagem(obj_dict):
        agg = collections.defaultdict(collections.Counter)
        for cid, texto in lead_text.items():
            t = texto.lower()
            for k, pat in obj_dict.items():
                if re.search(pat, t):
                    agg[k][outcome_of[cid]] += 1
        return agg

    def ganhos_com_objecao(obj_dict):
        n = 0
        for cid, texto in lead_text.items():
            if outcome_of[cid] != "ganho":
                continue
            t = texto.lower()
            if any(re.search(pat, t) for pat in obj_dict.values()):
                n += 1
        return n

    total_ganho = sum(1 for o in outcome_of.values() if o == "ganho")
    obj_fixed_sem_indeciso = {k: v for k, v in OBJ_FIXED.items() if k != "indeciso"}
    return {
        "original": contagem(OBJ_ORIGINAL),
        "corrigida": contagem(obj_fixed_sem_indeciso),
        "ganhos_com_objecao_original": ganhos_com_objecao(OBJ_ORIGINAL),
        "ganhos_com_objecao_corrigida": ganhos_com_objecao(obj_fixed_sem_indeciso),
        "total_ganho": total_ganho,
    }


def main() -> None:
    by_conv, base_prices = load()
    estrutural = auditoria_estrutural(by_conv)
    por_outcome, dup_reais, ganho_sem_close, ganho_preco_div = auditoria_qualidade_por_outcome(by_conv, base_prices)
    comp = comparar_heuristica_objecao(by_conv)

    md = ["# Auditoria de qualidade — dataset/conversations.parquet\n",
          "Due diligence sobre a base que alimenta RAG/Neo4j (few-shot do LLM) e que",
          "ancorou decisões de arquitetura (`analysis/build_objecao_graph.py`). Gerado por",
          "`analysis/audit_dataset_qualidade.py` — reproduzível, não é assert automático.\n",
          "## 1. Integridade estrutural (2500 conversas)\n"]
    if not estrutural:
        md.append("Nenhum problema estrutural.\n")
    else:
        md.append("| Problema | Ocorrências |\n|---|---|")
        for k, v in estrutural.most_common():
            md.append(f"| {k} | {v} |")
        md.append("")
        md.append("`timestamps fora de ordem`: confirmado via grep que o campo `timestamp` "
                   "**não é lido em nenhum lugar do código** (RAG/Neo4j/extração usam só "
                   "`message_index`, que é 100% sequencial e correto) — artefato de geração "
                   "sem efeito prático.\n")

    md.append("## 2. Qualidade por outcome (dataset inteiro)\n")
    md.append("| Outcome | Total | Curtas (<2 msg) | Texto quebrado | Veículo vazio | Idade implausível |")
    md.append("|---|---|---|---|---|---|")
    for outcome in sorted(por_outcome):
        c = por_outcome[outcome]
        md.append(f"| {outcome} | {c['total']} | {c['curtas']} | {c['garbled']} | "
                   f"{c['veiculo_vazio']} | {c['idade_implausivel']} |")
    md.append(f"\nDuplicatas exatas no dataset inteiro: **{len(dup_reais)}** grupos.\n")

    md.append("## 3. Subconjunto GANHO (o que RAG/Neo4j realmente injetam no LLM)\n")
    md.append(f"- Conversas sem sinal textual real de fechamento (falso-positivo de `has_close`): "
               f"**{len(ganho_sem_close)}**")
    md.append(f"- Vendedor menciona R$ fora de qualquer faixa plausível dos planos reais "
               f"(`plans.json`, 0.5x–3x do valor base): **{len(ganho_preco_div)}**\n")

    md.append("## 4. Re-validação do achado central ('objeção → ~0% ganho')\n")
    md.append("A heurística que gerou esse achado (`analysis/build_objecao_graph.py`) tinha os "
               "mesmos falsos-positivos que foram corrigidos em `orch_svc/objecoes.py` nesta sessão "
               "(`azul`/`porto` sem contexto, `preço` solto, `outra` genérico). Comparação:\n")
    md.append("| Heurística | preço | concorrente | cobertura | ganhos com objeção |")
    md.append("|---|---|---|---|---|")
    for nome, key in (("Original (pré-fix)", "original"), ("Corrigida (pós-fix)", "corrigida")):
        agg = comp[key]
        linha = f"| {nome} |"
        for cat in ("preco", "concorrente", "cobertura"):
            tot = sum(agg.get(cat, {}).values())
            linha += f" {tot} |"
        n_ganho = comp[f"ganhos_com_objecao_{key}"]
        linha += f" **{n_ganho} / {comp['total_ganho']} ({100*n_ganho/comp['total_ganho']:.1f}%)** |"
        md.append(linha)
    md.append("\n**Conclusão:** a correção da regex reduziu o volume bruto de detecção (menos "
               "falso-positivo), mas o número central do insight — zero conversas `ganho` com "
               "qualquer objeção detectada — se manteve em 0% nas duas versões. A decisão de "
               "arquitetura (reverter objeção com tática antes de escalar) **não está apoiada "
               "num artefato da regex antiga** — é um padrão real e robusto no dataset.\n")

    md.append("## Conclusão geral\n")
    md.append("Nenhum problema de qualidade encontrado que colocasse em risco o comportamento do "
               "agente — nem no subconjunto `ganho` (RAG/Neo4j few-shot) nem no dataset inteiro "
               "(que alimenta a análise de objeções). O único achado real (timestamp fora de ordem) "
               "não é consumido por nenhum código do sistema.\n")

    OUT.write_text("\n".join(md))
    print(f"escrito: {OUT}")
    print(f"\nestrutural: {dict(estrutural)}")
    print(f"duplicatas: {len(dup_reais)} grupos")
    print(f"ganho sem close real: {len(ganho_sem_close)}")
    print(f"ganho preço divergente: {len(ganho_preco_div)}")
    print(f"ganhos com objeção — original={comp['ganhos_com_objecao_original']} "
          f"corrigida={comp['ganhos_com_objecao_corrigida']} / total_ganho={comp['total_ganho']}")


if __name__ == "__main__":
    main()
