# Verlies-inventarisatie over de pijplijn

> Read-only, uit bestaande run-audits (`runs/` + de bake-off-eval-run). Doel: zien WAAR documenten
> verdwijnen, zodat de optimalisatie-volgorde door gemeten verlies wordt bepaald, niet door intuïtie.
> Volgorde: ingest → validity → relate(dedup) → scope-filter → retrieve(embed) → rerank → select.

## A. EVAL-corpus (gelabeld, qrels) — `real-nl.ab3.2i.2023.1-1006`, gate UIT (`--no-llm`)

Bron: bake-off-audit `embed-rounds/4b/audit.jsonl`. 1006 docs, **206 relevant** (qrels).

| stap | in-scope vooraf | gedropt | in-scope erna | reden | **relevant gedropt** |
|---|---:|---:|---:|---|---:|
| ingest | — | — | 1006 | bron ingelezen | — |
| validity | 1006 | **319** | 687 | `empty-after-ocr` (<50 leesbare tekens) | **53** |
| relate (dedup) | 687 | 0 | 687 | 951 dup-edges gemarkeerd; collapse uitgesteld naar `select` (D20.5) | 0 |
| scope-filter | 687 | **542** | **145** | 422 thread-tail + 120 process-notification (regels-only, geen e-mail-LLM) | **27** (thread-tail) |
| retrieve (embed) | 145 | 0 | 145 | embedder rankt alle 145 | 0 |
| rerank | 145 | 0 | 145 | BM25 herordent | 0 |
| select | 145 | cutoff/collapse | ≤145 | target=206 ≥ 145 → geen cutoff-drop; dup-collapse | 0 |

Reconciliatie: 319 + 542 = 861 = `scope-complete.excluded`; 1006 − 861 = 145 = `undecided` (= `first-pass`-lengte). ✓

**Markeringen:**
- **Grootste absolute drop:** scope-filter (542), gedomineerd door de **thread-tail-regel (422)**. Maar
  dit is vooral niet-relevante e-mail-padding — correcte uitsluitingen voor precisie.
- **Waar RELEVANTE docs verloren gaan:** 80/206 vóór retrieve — **53 door validity** (<50 tekens) +
  **27 door thread-tail**. Validity is dus de grootste relevant-verlies-hefboom op dit corpus, niet
  thread-tail. (process-notification dropt 120 docs, daarvan 0 relevant.)
- **Uitdunnings-confound van de bake-off:** de embedder bereikte **145/1006** docs, waarvan 126 relevant
  (87% relevante dichtheid → te weinig speelruimte om embedders te scheiden). De uitdunning kwam
  vólledig van validity (−319) + scope-filter-regels (−542). Beide zijn **e-mail-specifiek** op dit
  synthetische corpus.

## B. BZK-corpus (echt, PDF) — `runs/bzk-C-cloud{,-v2}`, gate UIT

Bron: `runs/bzk-C-cloud/audit.jsonl`. 1000 PDF-docs, geen qrels.

| stap | in-scope vooraf | gedropt | in-scope erna | reden |
|---|---:|---:|---:|---|
| ingest | — | — | 1000 | — |
| validity | 1000 | **0** | 1000 | PDF-tekst ruim boven 50 tekens |
| relate (dedup) | 1000 | 111* | 889 | 111 dup-edges; in deze (oudere) run uitgesloten via de inmiddels verwijderde `rule_duplicate` |
| scope-filter | 889 | 0** | 889 | **geen e-mailregel vuurt op PDF** (0 thread-tail/forwarded/calendar/process-notif) |
| retrieve … | 889 | … | … | — |

\* In de huidige code sluit dedup niet pre-retrieve uit; de collapse verschuift naar `select`. \*\* De
111 `scope-complete.excluded` in deze run zijn de oude dup-regel, niet de e-mailregels.

**Markering:** op een PDF-dossier is er **nagenoeg geen pre-retrieve recall-verlies** uit validity of de
scope-regels — de uitdunning die de bake-off zo confoundde is een e-mail-corpus-artefact en speelt hier
niet.

## C. Gooise Meren (echt, PDF) — `runs/converge-blind-…`, gate AAN (`qwen3:0.6b`)

Bron: `runs/converge-blind-20260625-201522/audit.jsonl`. 414 docs.

| stap | in | gedropt | erna | reden |
|---|---:|---:|---:|---|
| ingest | — | — | 414 | — |
| validity | 414 | 11 | 403 | empty-after-ocr |
| relate | 403 | 50 | … | dup-edges |
| scope-filter (**LLM AAN**) | … | **410 totaal** | **4** | **scope-LLM: 349× UITSLUITEN / 4× BEHOUDEN** |
| retrieve | 4 | — | 4 | trechter dichtgeklapt |

**Markering:** de scope-LLM-gate op een te klein model is veruit het grootste verlies: **~99%**
(414 → 4). Dit overschaduwt elke andere stap.

## Conclusie — optimalisatie-volgorde op basis van gemeten verlies

1. **Scope-LLM-gate (wanneer AAN op een klein model) — ACTIEF, dominant.** 99% verlies (Gooise Meren
   414→4, 349 UITSLUITEN). Dit is de #1 recall-vernietiger. Al gemitigeerd door de gate uit te zetten;
   wil je tóch een gate, dan is de modelgrootte de hefboom, niet de regels.
2. **Met de gate UIT is het verlies corpus-afhankelijk:**
   - **E-mail-corpus:** de **validity-50-tekensgrens** is de grootste relevant-verlies-hefboom
     (53/80 relevant), daarna thread-tail (27, latent — zie scope-filter.md).
   - **PDF-corpus (de echte BZK-use-case):** vrijwel geen pre-retrieve recall-verlies; validity 0,
     scope-regels 0.
3. **Dedup (relate)** markeert veel maar dropt in de huidige code niet pre-retrieve (collapse in
   `select`) — geen recall-hefboom pre-retrieve.

**Kernpunt:** de embedder-vraag was geen embedder-probleem maar een uitdunnings-confound dat
*e-mail-specifiek* is; op de echte PDF-dossiers bestaat die uitdunning niet. Eerst optimaliseren waar de
data het verlies aanwijst: de scope-LLM-gate (als ooit aangezet) en — alleen voor e-mail-corpora — de
validity-grens. Niet de embedder.
