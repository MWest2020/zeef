# Changelog

Alle noemenswaardige wijzigingen aan dit project worden hier vastgelegd.
Formaat losjes gebaseerd op [Keep a Changelog](https://keepachangelog.com/nl/);
versies volgen [SemVer](https://semver.org/lang/nl/).

## [Unreleased]

### 2026-06-24 — feat: viewer-ui — self-contained, offline `report.html` + `excluded.json`

**Waarom:** de criteria eisen dat het resultaat controleerbaar is — **zowel de geselecteerde ~100
als de rest** — en dat de deelonderwerpen als keuzemenu aan de verzoeker voorgelegd kunnen worden.
Een ruwe `inventory.xlsx` + losse JSON is dat niet. Eén self-contained HTML-rapport maakt dit
tastbaar en is tegelijk de zichtbare navolgbaarheids-/soevereiniteitsdemo.

**Wat (change #4 `viewer-ui`):**
- `src/zeef/templates/report.html` (nieuw) — **single-file**, read-only rapport: EUPL-1.2-header,
  system fonts, vanilla JS, **geen** CDN / externe fonts / externe scripts / `fetch`. De run-data
  staat inline in een `<script type="application/json">`-blok; opent met `file://`, air-gapped.
  Toont de kern als inklapbaar onderwerp/deelonderwerp-menu (per document score/motivatie/
  samenvatting/reden/relaties + gelakt-status) en de uitgesloten rest per reden.
- `export.py` — `write_excluded` → **`excluded.json`** (volledige uitgesloten set + redenen,
  validity vs semantisch); `build_report_data` (alléén presentatievelden, geen documenttekst;
  gelakt-status uit de canonieke `REDACTION_META_KEY`); `write_report_html` injecteert de data en
  escapet `<`/`>`/`&` zodat documentinhoud het `<script>`-blok niet kan afsluiten.
- `pipeline/run.py` (additief) — `report.html` + `excluded.json` in de export-stap en in de
  audit-artefactenlijst.

**Security/soevereiniteit:** alle onvertrouwde tekst (LLM-samenvatting/labels, titels) wordt bij het
renderen via de DOM-tekstweg geëscaped (geen `innerHTML` van onvertrouwde data), bovenop de
inline-JSON-escaping. Het rapport haalt niets extern op — getest.

**Tests:** `test_viewer.py` — offline/geen externe requests (geen URL/`fetch`/externe script/link),
escaping (een `<script>`-payload verschijnt alleen geëscaped, niet als live tag), uitgesloten set per
reden (validity vs semantisch), gelakt-status uit `REDACTION_META_KEY`. `openspec validate viewer-ui
--strict` ✓. `pytest` mét cloud 107/1, zónder cloud 104/4 (schone collectie). `ruff` schoon.

### 2026-06-24 — fix: review-bevindingen op output-hygiene (formule-injectie + bedrading)

**Waarom:** review op `change/output-hygiene` leverde één security-fix en twee kleinere punten op.

**Wat (`export.py`, alleen deze change):**
- **🟠 Excel/CSV-formule-injectie (CWE-1236).** `write_inventory` schreef tekstcellen rauw; een cel
  die met `=`, `+`, `-`, `@` (of tab/CR) begint, voert Excel/LibreOffice uit bij openen — en de
  inventory wordt door een ambtenaar in Excel geopend, met kolommen uit onvertrouwde LLM-bron. Nieuwe
  `_formula_safe`-helper prefixt zulke tekstcellen met een apostrof (tekst i.p.v. formule).
  **Dekt expliciet álle tekstkolommen**, niet alleen de nieuwe `summary`: ook de **bestaande**
  `category` (change #2), `reason` en `motivatie` (change #1/#2) worden nu geneutraliseerd — vandaar
  dat een output-hygiene-change ouder kolomgedrag raakt. Test leest de geschreven celwaarde terug
  (`'=…` geprefixt; onschuldige cel ongewijzigd).
- **e2e-assert op de summary-bedrading.** `include_summary = not no_llm` was alleen op functieniveau
  getest; nu ook een volledige `--no-llm`-run die bevestigt dat de geëxporteerde `inventory.xlsx`
  géén `summary`-kolom heeft (legt de bedrading vast tegen een stille refactor).
- **Docs:** de-pijplijn benoemt nu expliciet dat de samenvatting de **opening** (~2000 tekens) van
  het document dekt, niet het volledige document.

**Tests:** `pytest` mét cloud / zónder cloud beide groen (zónder collecteert nog steeds schoon).
`openspec validate output-hygiene --strict` ✓; `ruff` schoon.

### 2026-06-24 — feat: output-hygiene — samenvatting, overlaps-with, test-collectie zonder cloud-dep

**Waarom:** drie restpunten die een slordige indruk geven bij een auditor: een `summary`-kolom die
nooit gevuld werd (lege kolom met header), `overlaps-with` als dood contract (gedeclareerd, nooit
uitgestoten), en een testsuite die niet collecteerde zonder de optionele `cloud`-dep.

**Wat (change #3 `output-hygiene`):**
- `pipeline/summarise.py` (nieuw, capability `summarise`) — per geselecteerd document één LLM-call →
  ≤`summary_max_words` (100) inhoudssamenvatting (wát het document zegt, los van de `rationale` =
  waaróm het scoort), ná `select` en `topics`. Prompt/model/locatie gelogd. Onder `--no-llm`:
  geen samenvatting, **geen model-call**.
- `export.py` — `write_inventory(..., include_summary)`: de `summary`-kolom verschijnt alleen mét
  LLM; onder `--no-llm` wordt ze **weggelaten** (geen lege kolom). `run.py` zet
  `include_summary = not providers.no_llm`.
- `pipeline/dedup.py` + `relate.py` — `overlaps-with` voor partiële overlap: bevestigde cosine in
  `[overlap_threshold, near_dup_threshold)` → `overlaps-with` (evidence = de cosine); op/boven
  near-dup blijft `duplicate-of`. Hergebruikt de bestaande near-dup-cosine. `overlap_threshold`
  (0.7) in `config.py`, gelogd in het manifest.
- `config.py` — `overlap_threshold` + `summary_max_words` (eigen blok). `run.py`/`cli.py` additief:
  `summarise`-stage in de timer, beide params doorgegeven + in manifest-params.
- `tests/test_cloud_auth.py` — **fix:** module-niveau `import anthropic` → lazy via
  `pytest.importorskip` in de fixture (+ in de api-key-test die `complete()` raakt). De suite
  collecteert nu zónder `--extra cloud` en de cloud-only tests skippen netjes als de dep ontbreekt.

**Determinisme/soevereiniteit:** `overlaps-with` is deterministisch; de samenvatting is de enige
generatieve toevoeging (temp 0 via de driver, prompt gelogd); `--no-llm` blijft air-gapped en laat
de kolom weg.

**Tests:** `test_summarise.py` (samenvatting gezet + prompt gelogd + ≤max woorden; `--no-llm` geen
call/geen summary), `test_dedup.py` (scharnierend paar: net ónder near-dup → `overlaps-with`, op/boven
→ `duplicate-of`), `test_export.py` (kolom afwezig onder `include_summary=False`, op kolomnaam).
`openspec validate output-hygiene --strict` ✓. `uv run pytest` **mét** cloud: 101 passed / 1 skipped;
**zónder** cloud: 98 passed / 4 skipped (schone collectie, cloud-tests geskipt). `ruff` schoon.

### 2026-06-24 — fix: review-bevindingen op de validity-gate (robuustheid + precisie)

**Waarom:** review (`/review` + `/security-review`) op `change/pdf-validity-gate` legde drie
acteerbare punten bloot.

**Wat:**
- `loaders/pdf_loader.py` — `_extract_text` ving alleen `(PyPdfError, OSError, ValueError)`. pypdf
  gooit op vijandige invoer óók `KeyError`/`struct.error`/`RecursionError`; die vielen door naar
  ingest's brede catch en werden *gedropt* i.p.v. als `parse_ok=false` vastgelegd — in strijd met
  de "recorded, not dropped"-eis. Verbreed naar `except Exception` (zoals ingest zelf), zodat een
  corrupt document consequent een document mét `parse_ok=false` wordt en de gate het afhandelt.
- `health.py` — Woo-annotatie-regex `5\.1\.[125]\w?` overmatchte gewone artikelnummers (`5.1.10`,
  `5.1.2a`) en blies `redaction_ratio` op voor niet-gelakte tekst. Vervangen door opgesomde
  suffixen `5\.1\.(?:1|2e?|5)`. (Errde naar behouden, dus geen valse uitsluiting — wel valse
  "gelakt"-markering.)
- `pipeline/validity.py` — `from langdetect import detect` stond ín `_language_signal` (per
  document her-uitgevoerd). Naar module-niveau gehesen, één keer geprobeerd bij import.
- `pipeline/validity.py` — **besluit op review-#2:** `metadata["redaction_note"]` is de *canonieke,
  duurzame* "vermoedelijk gelakt"-markering; `decision_reason` is een vluchtige echo (select() en
  scope-filter overschrijven die downstream). Vastgelegd in `REDACTION_META_KEY` + comments, zodat
  inventory/export en de viewer (change #4) de metadata lezen, niet `decision_reason`.

**Niet gewijzigd (bewust):** dubbele defaults in `run.py` vs `config.py` — dat spiegelt de
bestaande conventie (`relate.py`'s `DEFAULT_NEAR_DUP_THRESHOLD` vs `Settings.near_dup_threshold`).

**Tests:** `tests/test_validity.py` +1 (`test_woo_annotation_does_not_overmatch_ordinary_article_numbers`).
Gelakt-behoud- en grens-test blijven groen (de grens-test scharniert op expliciete ratio-overrides,
los van de regex). Volledige suite: `pytest` **82 passed / 1 skipped**; `ruff` schoon;
`openspec validate pdf-validity-gate --strict` ✓.

### 2026-06-24 — feat: validity-gate — deterministische pre-flight voor de PDF-pivot

**Waarom:** de verkenning draait op een **PDF-only** dataset. De e-mailvormige exclusie-regels
(forwarded-only, no-reply, thread-heuristiek) vuren daar niet, dus niets beschermde de
relevantiefase tegen *mechanisch onbruikbare* documenten (mislukte OCR, corrupt/leeg PDF). Een
corrupt of leeg document in de top-100 is zichtbare ruis die een beoordelaar direct wantrouwt. De
val: zwaar-**gelakte** documenten bevatten legitiem weinig tekst — een naïeve leeg-drempel zou die
vals uitsluiten (recall-verlies, slecht live). De gate onderscheidt *onbruikbaar* van *gelakt*.

**Wat (change #1 `pdf-validity-gate`, deterministisch, geen LLM):**
- `health.py` (nieuw) — `redaction_ratio()` + `health_metadata()`: deterministische extractie-
  gezondheid (`char_count`/`parse_ok`/`redaction_ratio`) als pure functies over reeds
  geëxtraheerde tekst. Redactiesignaal = zwartlak-glyphs + lakmarkeringen (`[gelakt]`/`[…]`) +
  Woo-annotaties (`5.1.2e`, `10.1`, …).
- `pipeline/validity.py` (nieuw) — `validity_gate(...)`: volgorde `parse_ok` → leeg-na-OCR
  (redaction-aware) → taal (zacht, sluit nooit uit). Harde faal → `out_of_scope` +
  `validity:corrupt-pdf` / `validity:empty-after-ocr` + audit-event (id/check/reden). Gelakt-maar-
  leesbaar → behouden, gemarkeerd, blijft `undecided`. Ontbrekende metadata → default bruikbaar
  (nooit vals uitsluiten).
- `loaders/pdf_loader.py` — zet gezondheidsmetadata; corrupte PDF faalt **zacht** (`parse_ok=false`,
  document blijft bestaan i.p.v. weggegooid). `loaders/email_loader.py` — gezondheid voor
  uniformiteit (elk geïngest document draagt de velden).
- `config.py` — `validity_min_chars` (50) + `redaction_ratio_threshold` (0.10), bewust
  conservatief richting behouden; in het manifest vastgelegd.
- `pipeline/run.py` — `validity`-stage tussen `ingest` en `relate`, in de timer; `validity_excluded`
  als aparte telcategorie; manifest-params. `cli.py` — `--min-chars`/`--redaction-ratio` +
  validity-kolom in de samenvatting.

**Bewust niet in de gate:** exacte/near-duplicaten — die worden al deterministisch afgehandeld in
relate + scope-filter (`rule_duplicate`); twee code-paden voor duplicaten zou alleen verwarren.

**Tests:** `tests/test_validity.py` (9) — onbruikbaar uitgesloten met juiste reden, gelakt
behouden+gemarkeerd, bruikbaar ongewijzigd, geen LLM-call, ontbrekende metadata → bruikbaar,
`redaction_ratio` schoon=0. Plus de asymmetrische faalmodus expliciet: een zwaar gelakt document
onder `min_chars` overleeft de gate (undecided, gemarkeerd, eligible voor retrieve/score, níét in
de validity-telling), en een grens-test die bij gelijke tekstlengte bewijst dat alléén de
`redaction_ratio` het onderscheid maakt (net onder de drempel → `empty-after-ocr`; net erboven →
behouden). `openspec validate pdf-validity-gate --strict` ✓. `pytest` 81 passed /
1 skipped (cloud-auth-collectiefout = ontbrekende optionele `anthropic`-dep in deze worktree-venv,
los van deze change); `ruff` schoon. Spec: `openspec/changes/pdf-validity-gate/`.

### 2026-06-24 — fix: review-bevindingen op topic-clustering (run-crash + schaal)

**Waarom:** review (`/review` + security) op `change/topic-clustering` legde twee acteerbare
code-punten bloot vóór de merge.

**Wat (`pipeline/topics.py`, alleen deze change):**
- **🔴 nul-vector-guard (run-crash).** `_chunk_vectors` filterde nul-/niet-eindige chunk-embeddings
  niet; cosine is daar ongedefinieerd en `scipy.linkage` gooit hard (`ValueError: condensed distance
  matrix must contain only finite values`). Dat raakt direct de gelakt-maar-behouden documenten uit
  change #1 (dunne tekst). Nu gefilterd; houdt een document geen bruikbare chunk over, dan gaat het
  deterministisch naar **"Overig"** i.p.v. de run laat te laten crashen. Test:
  `test_empty_chunk_document_routes_to_overig_without_crashing`.
- **🟠 `linkage` één keer + chunk-cap (T8).** `_flat_clusters` werd twee keer aangeroepen → `pdist`
  dubbel berekend. Nu `_two_level`: één `linkage`, twee `fcluster`-cuts — halveert de kost en maakt
  de nesting bewijsbaar (zelfde dendrogram). De O(n²)-afstandsmatrix wordt begrensd via een
  **deterministische chunk-cap** (`max_chunks_per_doc`, default 40): gelijkmatige bemonstering over
  het document (geen "eerste/langste N", die de meerderheid zou biasen), zodat de topic-verdeling —
  en dus de T7-meerderheidsregel — behouden blijft. De cap staat in het run-manifest (geen stille
  truncatie). Besluit T8 in `design.md`. Test: `test_chunk_cap_preserves_majority`.

**Bevestigd, niet gewijzigd:** `_chunk_vectors` valt onder `--no-llm` terug op `embed.embed(...)` als
embeddings ontbreken — dat is een lokale embedding, **geen** LLM-call (de no-call-test blijft groen);
bewust en gedocumenteerd in de docstring.

**Tests:** `pytest` **86 passed / 1 skipped** (+2). Expliciet groen: reproduceerbaarheid, no-call,
T7-meerderheid, nul-vector→Overig, cap-behoudt-meerderheid. `openspec validate topic-clustering
--strict` ✓; `ruff` schoon; `topics.py` 177 regels (≤200).

### 2026-06-24 — feat: topic-clustering — onderwerp/deelonderwerp-menu voor de verzoeker

**Waarom:** een hoofdcriterium van de verkenning is het opdelen van de kern in deelonderwerpen, als
keuzemenu voor de verzoeker. Dat ontbrak, en de `category`-kolom toonde misleidend het *bestandstype*
(`pdf_digital`) i.p.v. een thematische categorie.

**Wat (change #2 `topic-clustering`):**
- `pipeline/topics.py` (nieuw) — deterministische agglomeratieve clustering (cosine, average
  linkage) over de **chunk**-embeddings uit retrieve, geknipt op twee hoogtes → onderwerp (grof) en
  deelonderwerp (fijn, genest). "Overig"-collapse onder `min_cluster_size`. `scipy`/`numpy` lazy
  binnen de stage. **Aggregatieregel (design T7):** een document met chunks in meerdere clusters
  wordt toegewezen via **meerderheid** van zijn chunk-clusters; gelijkspel → de medoid-chunk, dan
  het kleinste id — zodat de "precies één onderwerp/deelonderwerp per document"-belofte hard is.
- `pipeline/topic_labels.py` (nieuw) — labelling, afgesplitst (≤200-regelgrens). Onder `--no-llm`:
  TF-IDF-fallbacklabels (distinctieve termen), **geen model-call**. Met LLM: één call per cluster op
  representatieve snippets (medoid + naaste leden) → kort Nederlands label, prompt/model/locatie
  gelogd. (Kwaliteits-pass op het demo-model is handmatig, niet in de tests.)
- `export.py` — inventory `category` herbestemd naar **onderwerp / deelonderwerp**; bestandstype
  behouden in eigen `doc_type`-kolom; `write_topics` → `topics.json` (het keuzemenu).
- `models.py` — `Document.topic`/`subtopic` (labels, geen identity).
- `config.py` — `onderwerp_distance`/`deelonderwerp_distance`/`min_cluster_size` (eigen blok,
  conservatief, in het manifest). `run.py` (additief) — topics-stage ná `select`, in de timer;
  clusterparameters in manifest-params; `topics.json` in de artefactenlijst. `cli.py` (additief) —
  samenvatting toont onderwerp/deelonderwerp-aantal.
- `pyproject`/`uv.lock` — `scipy` als directe dep (was transitief via `datasketch`).

**Canoniek topic-veld:** `Document.topic`/`subtopic` (gespiegeld in inventory `category` en
`topics.json`) zijn de enige representatie van de toewijzing — change #4 (viewer) leest die, niet de
ruwe chunk-clusters.

**Tests:** `tests/test_topics.py` — tweelaagse groepering + "Overig"-collapse; **reproduceerbaarheid**
(identieke embeddings/parameters → identieke toewijzing, params in het manifest, twee runs →
identieke `topics.json`); de **asymmetrische faalmodus** expliciet (een document met chunks over twee
clusters krijgt via meerderheid precies één onderwerp/deelonderwerp, deterministisch); **`--no-llm`
maakt geen enkele model-call** (assert) met fallbacklabels; en de **LLM-label-branch** echt getest
(label landt op het cluster, bron niet meer fallback, per cluster een audit-event met prompt/model/
locatie). `test_export.py` op kolomnaam i.p.v. -index. `openspec validate topic-clustering --strict`
✓. `pytest` **84 passed / 1 skipped**; `ruff` schoon; ≤200-regel ok.

### 2026-06-23 — feat: abonnement-modus voor de Claude-LLM (OAuth via `ant auth login`)

**Waarom:** de cloud-LLM kon alléén met een betaalde `ANTHROPIC_API_KEY` (pay-per-token). Net als
in het zusterproject `crible` wil de gebruiker runs via een Claude-**abonnement** kunnen draaien
(OAuth), dat tegen het plan telt i.p.v. per token.

**Wat (4 bestanden, port van crible's `llm.py`):**
- `config.py` — `Settings.auth_mode` (`api_key` | `subscription`).
- `drivers/cloud.py` — `ClaudeLLM(auth_mode=...)`. In abonnement-modus: bouwt de SDK-client
  **zonder** `api_key`, mét header `anthropic-beta: oauth-2025-04-20`, en **verwijdert een
  eventuele `ANTHROPIC_API_KEY` uit de omgeving** (met stderr-melding) zodat een achtergebleven
  betaalde sleutel nooit stilletjes credits verbruikt — de SDK kiest die anders vóór het OAuth-pad.
- `profiles.py` — geeft `settings.auth_mode` door aan `ClaudeLLM`.
- `cli.py` — vlag `--subscription`; impliceert de cloud-LLM-backend (embeddings/rerank blijven van
  het profiel) en zet `auth_mode`. De gekozen modus staat in het `run-start`-audit-event.

**Gebruik:** eenmalig `ant auth login`, dan bv.
`zeef converge ./docs -q "..." --profile sovereign --subscription` — lokale Ollama-embeddings +
Claude-LLM via abonnement.

**Tests:** `tests/test_cloud_auth.py` — abonnement popt de betaalde key, bouwt de client met de
OAuth-header en zonder `api_key`; api-key-modus faalt zonder sleutel en geeft de sleutel door.
`pytest` 76 passed / 1 skipped; `ruff` schoon.

### 2026-06-20 — feat: runtimes vastleggen — per-stage timing + run-manifest.json (vierde artefact)

**Waarom:** de audit-log had per event een `ts`, maar geen *bedoelde* meting van hoe lang een
stage duurde — runtimes waren hooguit af te leiden door timestamps te diffen. Voor het vergelijken
van runs (en profielen/modellen) en voor een navolgbaar prestatiebeeld is expliciete vastlegging
nodig.

**Wat (3 bestanden):**
- `src/zeef/pipeline/run.py` — elke stage wordt nu omhuld door een monotone `perf_counter`-timer
  (immuun voor klok-aanpassingen). Per stage komt er één `timing`-event in de audit-log
  (`elapsed_ms`), en aan het eind wordt een **`run-manifest.json`** weggeschreven: schema-versie,
  zoekvraag, providers (model + locatie per rol), criteria-bron + labels, cutoff, parameters,
  documenttelling en `runtime_ms` (totaal + per stage). Het manifest hangt ook op `RunResult`.
- `src/zeef/export.py` — `write_manifest()` (zelfde stijl als `write_relations`).
- `src/zeef/cli.py` — samenvatting toont totale runtime en noemt het vierde artefact.

**Tests:** `test_export.py::test_manifest_exported_as_json` en
`test_e2e.py::test_run_manifest_records_stage_runtimes` (alle 9 stages aanwezig met `elapsed_ms`,
totaal aanwezig, manifest op `RunResult`). `pytest` 72 passed / 1 skipped; `ruff` schoon.

**Eerste echte run (Woo):** dossier `nl.ab3.2i.2023.1` (UvA Woo-besluit "Innovation Center for
Artificial Intelligence", 7 PDF's uit de WooZM/`pid.wooverheid.nl`-cache van `zeef-eval`),
sovereign-profiel met Ollama (`qwen2.5:7b` + `qwen3-embedding:0.6b`). Levert echte gearticuleerde
criteria + gemeten per-stage runtimes op.

### 2026-06-19 — fix: thread-heuristiek crashte op gemengde tijdzones in echte e-mail

**Waarom:** een run over een echt e-mailcorpus (HiCAL/TREC Total Recall, topic 407, 2.719 docs)
crashte in de thread-heuristiek: `TypeError: can't compare offset-naive and offset-aware
datetimes`. Echte e-mail mengt `Date`-headers mét en zónder tijdzone; `_date` gaf bij parse soms
een naïeve, soms een aware datetime, en het sorteren van een onderwerp-groep mengde die.

**Wat (1 bestand):** `src/zeef/pipeline/threads.py` — `_date` geeft nu **altijd** een tz-aware
datum (naïef → UTC). Test toegevoegd (`test_relate.py`: gemengde tz-headers sorteren zonder
crash). Raakt alleen de heuristische val-terug (header-loze mail); bestaande threads ongemoeid.
`pytest` 70 passed / 1 skipped; `ruff` schoon.

### 2026-06-19 — scope-filter-LLM recall-georiënteerd (UITSLUITEN/BEHOUDEN)

**Wat (`scope_filter.py`):** de LLM-twijfelstap was precisie-gericht (sloot uit op NIET-RELEVANT).
Nu recall-georiënteerd, conform de TAR-filosofie van het project: de LLM sluit **alléén** uit wat
met zekerheid buiten scope valt (eerste woord `UITSLUITEN`) en behoudt al het andere; de
precisie-verfijning gebeurt later in de relevantiescoring. Recall-veilige parse (`_is_exclude_verdict`:
alleen het eerste woord telt, "niet uitsluiten"/leeg → behouden). System+prompt herschreven.

**Waarom + gemeten effect:** op het echte dossier `nl.ab3.2i.2023.1` (6 kern-docs in 1.006) zette
de oude filter (qwen2.5:7b) 4 van de 6 echte overeenkomsten ten onrechte op NIET-RELEVANT — maar
2/6 haalden de scoring. Met de recall-filter: scope-LLM gaf 21× BEHOUDEN, 1× UITSLUITEN →
**5 van de 6 echte docs halen nu de scoring** (doc.1/5/6 hersteld; alleen doc.2 nog uitgesloten).
De scoring differentieert ze daarna (0,95 / 0,75 / 0,65 / 0,2). Afruil: recall omhoog kost
LLM-tijd (9 min vs 4,5 min op 1.006 docs — meer overlevenden = meer scoring-calls).

**Tests/docs:** `test_scope_filter.py` uitgebreid (recall-veilige verdict-parse; UITSLUITEN sluit
uit). `de-pijplijn.md` + `architectuur.md` bijgewerkt. `pytest` 69 passed / 1 skipped; `ruff` schoon.

### 2026-06-19 — near-dup-drempel instelbaar (`--near-dup`) + recall-bevinding op echt dossier

**Wat (per bestand):** de near-duplicate-cosinusdrempel was hardcoded op 0,9 in `relate()`. Nu
instelbaar via `config.py` (`near_dup_threshold` / `ZEEF_NEAR_DUP_THRESHOLD`), doorgegeven door
`run.py` (`run_converge(..., near_dup_threshold=)`) en de CLI-vlag `--near-dup`. `run-start`-audit
logt de waarde. Docs (`aan-de-slag.md`, `de-pijplijn.md`) bijgewerkt.

**Waarom + bevinding:** afgestemd op het echte dossier `nl.ab3.2i.2023.1` (6 echte kern-docs in
een corpus van 1.006). Sweep over drempels 0,80–0,99, deterministisch (`--no-llm`, om dedup van
LLM-ruis te isoleren): **de 6 echte kern-docs overleven bij élke drempel (6/6) en geen enkele
wordt als near-duplicate gevouwen.** De drempel regelt hier alleen hoeveel synthetische
thread/dup-ruis samenvouwt (18 kandidaten bij 0,80 → 130 bij 0,99). Conclusie: op dit dossier is
de near-dup-drempel **geen** recall-hefboom; 0,9 is veilig voor de kern. Dit corrigeert de eerdere
hypothese dat over-dedup recall kostte.

**De échte recall-bottleneck (gemeten):** de binaire scope-filter-LLM (qwen2.5:7b) zette 4 van de
6 echte samenwerkingsovereenkomsten ten onrechte op NIET-RELEVANT; de 2 die er doorheen kwamen
scoorden 0,95. De recall-hefboom voor 26 juni is dus het scope-filter-model/-prompt (of een
zachtere scope-policy), niet dedup. `pytest` 67 passed / 1 skipped; `ruff` schoon.

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
