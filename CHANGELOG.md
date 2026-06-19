# Changelog

Alle noemenswaardige wijzigingen aan dit project worden hier vastgelegd.
Formaat losjes gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/);
versies volgen [SemVer](https://semver.org/lang/nl/).

## [Unreleased]

### 2026-06-19 — change #2 (`criteria-scoring`): twee LLM-momenten met motivatie

**Waarom:** de relevantie in change #1 was dun en lastig te verdedigen — een kale zoekvraag (de
relevantiedefinitie nooit expliciet) en een `final`-score zonder onderbouwing (de lexicale
rerank). Voor 26 juni is de differentiator een **verdedigbare, uitlegbare** selectie: criteria
die een beoordelaar kan lezen én betwisten, plus een motivatie per document. Dat is precies waar
een LLM thuishoort — oordeel onder taalkundige ambiguïteit zónder mechanische grondwaarheid, en
waar een motivatie de verdedigbaarheid verhoogt.

**Wat (per bestand):**
- `models.py` — `Criterion`/`Criteria`-modellen + `Document.rationale` (per-document motivatie,
  los van de mechanische `decision_reason`).
- `pipeline/criteria.py` (nieuw) — `articulate_criteria`: één LLM-call zet de zoekvraag om in
  3–6 benoemde criteria; tolerante `label: omschrijving`-parse; onder `--no-llm` deterministische
  terugval op één criterium = de ruwe zoekvraag (geen call). Prompt + criteria gelogd.
- `pipeline/score.py` (nieuw) — `score`: de LLM scoort de top-K reranked kandidaten tegen de
  criteria (0–100 → `llm_relevance`) mét motivatie; `final = llm_relevance`. Kandidaten buiten
  de top-K worden expliciet gedemoveerd (gelogd, niet stil gedropt). Tolerante parse: onparseerbaar
  → score 0 + ruwe tekst, nooit een crash. Onder `--no-llm` slaat de stage over (final = rerank).
- `config.py` — `llm_score_top_k` (default 250). `cli.py` — `--score-top-k`; samenvatting toont de
  criteria-bron + aantal. `pipeline/run.py` — criteria als eerste stage, score tussen rerank en
  select; `criteria` in `RunResult`.
- `export.py` — inventory krijgt een **motivatie**-kolom; nieuwe `write_criteria` → `criteria.json`.
- Docs (`de-pijplijn.md`, `architectuur.md`, `roadmap.md`, README) + presentatie (`index.html`,
  nieuwe slide over criteria + uitlegbare scoring) in sync gebracht.
- OpenSpec change `openspec/changes/criteria-scoring/` (proposal, design met D9–D13, tasks,
  spec-deltas: `criteria` ADDED, `retrieve-rerank`/`export` MODIFIED).

**Bewijs:** volledige suite **67 passed, 1 skipped** (de live-model smoke); `ruff check src tests`
schoon; geen bestand > 200 regels. Echte LLM-smoke via Ollama: `--no-llm` schrijft de vier
artefacten met fallback-criterium; mét `qwen2.5:7b` levert criteria-articulatie zinvolle criteria
(*betrokken partijen, jaar, subsidie, begroting, initiatief*) en scoring een graduele score
(0,95) met motivatie per document. `--no-llm`-gedrag van change #1 blijft exact behouden. Niets
gepusht (afspraak: ik commit lokaal, push gebeurt door de gebruiker).

### 2026-06-19 — fix: OllamaEmbed crashte op grote echte PDF's (HTTP 500) — tekst afgekapt

**Waarom:** een end-to-end run op een ECHT WooZM-dossier (`nl.ab3.2i.2023.1`, opgehaald via
`zeef-eval fetch`/`build --core`) crashte in de relate/near-dup-stap. Root-cause: `OllamaEmbed`
stuurt de volledige documenttekst naar `/api/embeddings`; dat endpoint geeft **HTTP 500 bij ~99k
tekens** (bevestigd: 8k werkt, 99k faalt). Echte Woo-PDF's zijn fors (45k–99k tekens hier), dus
zeef zou op de aangeleverde 26-juni-set zijn omgevallen.

**Wat (1 bestand):** `src/zeef/drivers/ollama.py` — `OllamaEmbed.embed` kapt elke tekst af op
`char_budget` (default 8.000, instelbaar). Verantwoord: een embedding representeert vooral de
leidende inhoud (titel/partijen/onderwerp = waar het relevantiesignaal zit); het alternatief is
een crash. Raakt alleen de Ollama-embed; Voyage (cloud) en Hashing (lokaal) ongemoeid.

**Bewijs:** met de fix loopt `zeef converge` op de echte-data corpus (208 docs, 6 echt) volledig
door — 3 geselecteerd, doc_id-join 0 unmatched, gerealiseerde precision 1,00. `ruff` schoon.
Niets gecommit/gepusht.

### 2026-06-18 — LLM-backend losgekoppeld van profiel + tokenusage-logging (model-bake-off)

**Waarom:** een vergelijking van scope-filter-modellen (qwen2.5:7b, qwen3:0.6b, qwopus3.5
lokaal + Claude Haiku via cloud) op één vast 1000-doc corpus, met alle overige variabelen
constant. Het cloud-profiel koppelde LLM+embeddings+rerank (vereiste ook een Voyage-key); voor
een eerlijke A/B moest alleen het LLM kunnen wisselen.

**Wat (per bestand):**
- `config.py` — drie env-knoppen: `ZEEF_LLM_BACKEND` (`ollama`/`cloud`, default volgt profiel),
  `ZEEF_CLOUD_LLM_MODEL` (Claude-model-id, bv. een Haiku-model), `ZEEF_LLM_USAGE_LOG`
  (append-only JSONL met tokengebruik per cloud-call, voor kostenraming).
- `profiles.py` — `_resolve_llm` honoreert `llm_backend` los van het profiel; embeddings/rerank
  blijven van het profiel. Zo draait Haiku-LLM mét lokale (sovereign) embeddings + reranker.
- `drivers/cloud.py` — `ClaudeLLM` accepteert `usage_log` en logt input/output-tokens per call
  (nooit de sleutel). Cloud-extra (`anthropic`) geïnstalleerd via `uv sync --extra cloud`.

**Resultaat:** alle 4 modellen vrijwel identiek (recall ~0,10–0,11, nDCG ~0,25) — op een
thematisch-strak corpus domineren de deterministische dedup/thread-regels (~976/1000 uitgesloten
door regels, ~24 LLM-randgevallen). Tuning-hefboom voor 26 juni is de near-dup-drempel, niet het
model. Haiku-kost ~$0,006/run. `ruff` schoon, profiel-tests groen. Sleutel uit `.env`
(`ANTHROPIC_API_KEY`), nooit getoond/gecommit. Niets gepusht.

### 2026-06-17 — Sovereign smoke-run (model in de lus, Ollama + Qwen3)

**Wat:** gevalideerd dat het `sovereign`-profiel mét een model in de lus correct bedraad is
(CPU-only, bedradingstest — geen prestatietest). Ollama gestart, `qwen3:0.6b` (LLM) en
`qwen3-embedding:0.6b` (embed) gepulld, en `zeef converge --profile sovereign` (zónder
`--no-llm`) op de fixtures gedraaid.

**Gewijzigd (per bestand):**
- `drivers/ollama.py`: `OllamaLLM` krijgt `think` (default uit) + `num_predict`. Qwen3's
  redeneer-modus is voor een in/uit-scope-classificatie onnodig en op CPU onbetaalbaar traag;
  uitzetten bracht een call van >120 s naar ~0,4 s. De aan de stage doorgegeven prompt blijft
  ongewijzigd (audit legt exact díe prompt vast).
- `config.py`: `ollama_llm_model`, `ollama_embed_model` en `sovereign_embed` (`local`|`ollama`)
  als env-instelbare velden (`ZEEF_OLLAMA_LLM_MODEL`, `ZEEF_OLLAMA_EMBED_MODEL`,
  `ZEEF_SOVEREIGN_EMBED`). `profiles.py`: sovereign kan nu env-gestuurd `OllamaEmbed` kiezen
  (reranker blijft lokaal — Ollama heeft geen rerank-endpoint). Geen pijplijn-codewijziging.
- `tests/test_sovereign_smoke.py`: herhaalbare check (skipt zonder `ZEEF_SMOKE=1`/Ollama) met
  drie harde assertions — LLM-fallback afgegaan, elk LLM-event draagt model+`location=local`+
  exacte prompt, en een loopback-only socket-guard die elke externe call hard laat falen.

**Resultaat (bewijs uit `audit.jsonl`):** LLM-fallback ging af op **7** documenten; elk
`llm-decision`-event droeg `model=ollama:qwen3:0.6b`, `location=local` en de exacte prompt; de
embeddings liepen via `ollama:qwen3-embedding:0.6b` (`location=local`); **0** geblokkeerde
egress-pogingen (sovereign bleef sovereign). Offline suite: 57 passed, 1 skipped; ruff clean.

**Boundary:** go/no-go-gate gehaald. `zeef-eval` **niet** gebouwd, niet gearchiveerd, niet gepusht.

### 2026-06-17 — `converge-mvp` geïmplementeerd

**Wat:** de OpenSpec change `converge-mvp` uitgewerkt tot een werkende CLI. De volledige
pijplijn draait nu end-to-end, volledig air-gapped, met een groene testsuite.

**Waarom:** van gevalideerde specificatie naar een tool die op 26 juni op een aangeleverde
dataset kan draaien en een navolgbare selectie + audit-trail oplevert.

**Toegevoegd / gewijzigd (per bestand):**
- **Hygiëne:** dev-tooling (`pytest`, `ruff`) als PEP 735 `[dependency-groups]` zodat
  `uv run pytest`/`ruff` zonder `--with` werken; `pypdf` + `datasketch` van extra naar core-dep
  (default `sovereign`-profiel heeft ze nodig). De content-geadresseerde id verhuisd naar het
  afhankelijkheidsvrije `src/zeef/ids.py` (cross-repo `doc_id`-contract, digest gepind in
  `tests/test_ids.py`); `models.py` her-exporteert.
- **Providers/profielen:** `src/zeef/profiles.py` (`resolve_providers` → `ProviderBundle`).
  Drivers: `drivers/local.py` (deterministische `HashingEmbed` + `LexicalReranker`, de
  air-gapped default), `drivers/ollama.py` (host-gated), `drivers/cloud.py` (Claude + Voyage,
  key-gated, niet live getest). Gedeelde `src/zeef/similarity.py`.
- **Stages:** `pipeline/ingest.py`, `loaders/{email_loader,pdf_loader}.py` + registry;
  `pipeline/{relate,threads,dedup}.py`; `pipeline/{scope_filter,scope_rules}.py`;
  `pipeline/{chunking,retrieve,rerank}.py`; `pipeline/select.py`; `export.py`;
  `pipeline/run.py` (orkestratie). CLI `cli.py` volledig bedraad met `rich`-samenvatting.
- **Fixtures:** `tests/fixtures/corpus/` — 5-mail thread, exact + near-duplicaat, calendar-invite,
  procesnotificatie, mail met bijlage, digitale + tekstloze PDF, niet-ondersteund bestand.
- **Tests:** 57 tests over alle capability-scenario's; e2e met geblokkeerde sockets (air-gapped
  afgedwongen), bestandslengte-guard (≤200 regels). README + docs-site + dit changelog bijgewerkt.

**Afwijking (gemarkeerd):** de soevereine air-gapped default gebruikt deterministische lokale
providers i.p.v. een cross-encoder/Ollama-model, zodat de acceptatierun écht zonder netwerk en
zonder gewichten werkt. De modelgebaseerde drivers staan achter dezelfde interfaces (zie
`tasks.md` 3.3). Design.md voorzag dit al (risicoparagraaf: lokale-model-footprint).

**Tests:** `uv run pytest` → 57 passed; `uv run ruff check` clean; geen bestand > 200 regels;
`openspec validate converge-mvp --strict` slaagt.

**Boundary:** geïmplementeerd + gevalideerd, **niet** gearchiveerd — dat is een menselijk besluit
na review van de acceptatietest en de egress-vraag van 26 juni.

### 2026-06-17 — Projectinitiatie

**Wat:** repo opgezet, OpenSpec change #1 (`converge-mvp`) opgesteld en gevalideerd,
projectscaffold, Q&A-document, documentatie-site (Hugo) en HTML-presentatie aangezet.

**Waarom:** kickoff voor de technische verkenning Woo (BZK/ECP) op 26 juni 2026. De tool moet
die dag op een aangeleverde dataset + verfijnde zoekvraag draaien en een navolgbare selectie
opleveren.

**Toegevoegd:**
- Private GitHub-repo `MWest2020/zeef`; lokale git op `main`.
- OpenSpec geïnitialiseerd (schema `spec-driven`). Change `converge-mvp` met `proposal.md`,
  `design.md`, 10 capability-specs en `tasks.md` — `openspec validate --strict` slaagt (4/4
  artefacten compleet).
- Projectscaffold: `uv`-project (Python 3.12+), `pyproject.toml` met core-deps (pydantic v2,
  typer, rich, openpyxl) en optionele extras `sovereign`/`cloud`/`dev`.
- Canoniek datamodel `src/zeef/models.py` (`Document`, `Chunk`, `Relation`, content-geadresseerde
  id), interfaces `src/zeef/protocols.py` (`Loader`, `EmbeddingProvider`, `RerankerProvider`,
  `LLMProvider`), profielconfig `src/zeef/config.py` (incl. `NullLLM` voor `--no-llm`),
  audit-writer `src/zeef/audit.py` (append-only JSONL), CLI-skelet `src/zeef/cli.py`
  (`zeef converge` met cutoff-vlagvalidatie).
- Rooktests (`tests/test_models.py`) — 3 passed.
- `LICENSE` (EUPL-1.2, officiële SPDX-tekst), `README.md`, `.gitignore`.
- `hackathon/qa-technische-verkenning.md` — levend Q&A-document voor 26 juni.
- Documentatie-site (Hugo) in `docs/` en HTML-presentatie in `presentation/`.

**Licentie:** EUPL-1.2 (aansluitend bij Common Ground / NL-overheid).

**Tests:** `uv run pytest` → 3 passed.

**Nog te doen:** implementatie van de stages volgens `openspec/changes/converge-mvp/tasks.md`.
