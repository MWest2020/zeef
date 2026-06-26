# Lessons learned — zeef

Levend document. Geen formele deliverable; het geheugen van deze bouw — schaalcijfers,
parameter-gedrag, kwalitatieve bevindingen en methodische lessen die niet in de code of de
spec thuishoren, maar die we voor de presentatie en voor de volgende dossiers niet willen
verliezen. Bijwerken naarmate we verder leren.

Context: bevindingen komen grotendeels uit de `discover-mode`-bouw, gevalideerd op een echt
Woo-corpus van **414 PDF's (~1,7 GB)** van gemeente Gooise Meren e.o. — een breed gemengd
dossier (asielopvang/noodopvang, omgevingsvergunningen, stikstof, forten, windmolens,
mijnsteen). 11 documenten zijn fotoscans zonder tekstlaag en vallen terecht uit de validity-gate
(403 valide docs de pijplijn in).

## 1. Schaalbevindingen (echte getallen, lokale CPU, qwen3-embedding:0.6b via Ollama)

Embed-latency schaalt ~lineair met tekstlengte:

| Invoerlengte | Latency per embed |
|---|---|
| ~60 tekens | 0,12 s |
| 1.000 tekens (één chunk) | 0,77 s |
| 2.000 tekens | 1,54 s |
| 8.000 tekens (full-text default) | **7,7 s** |

Twee bottlenecks, in volgorde van ontdekking:
1. **Full-text near-dup-embed** (relate-stage): 403 docs × 8.000-char-embed ≈ 52 min — dit
   blies als eerste de timeout op. Opgelost door de afkaplengte instelbaar te maken
   (`ZEEF_OLLAMA_EMBED_CHARS`, default 8000) en op 2.000 te zetten → ~10 min.
2. **Chunk-embeds** (embed-stage): bij cap 6 → 2.418 chunks × 0,77 s ≈ 31 min, de tweede
   bottleneck. Cap 3 → ~15 min.

Een **volledige discover-run op 403 documenten duurt ~33 min lokaal** (ingest ~5 min,
relate ~12 min, embed ~16 min, clustering <2 s). Ingest (pypdf op 1,7 GB) en de Ollama-embeds
domineren; de scipy-clustering zelf is verwaarloosbaar.

## 2. Parameter-afhankelijkheid van de clustering

- De knip-afstanden (`onderwerp_distance`/`deelonderwerp_distance`) en `min_cluster_size` zijn
  **corpus-grootte-afhankelijk**. De converge-defaults zijn afgestemd op ~100-doc selecties en
  **deugen niet voor 400+ documenten**.
- De semantische embeddings leven in een **smalle cosine-cone**: de merge-hoogtes van het
  dendrogram lopen tot max 0,712, mediaan 0,234, p90 0,459. De converge-default
  `onderwerp_distance=0.8` ligt vóórbij het hoogste samenvoegpunt → knipt het hele corpus tot
  **één onderwerp**. De bruikbare band is ~0,2–0,5.
- **De offline doc-vector-sweep was niet voorspellend voor de echte chunk-niveau-clustering.**
  Een sweep op één full-text-vector per document voorspelde ~17% Overig bij (0.45/0.38/mcs10);
  de échte run (chunk-vectoren, cap 3, meerderheids-aggregatie) gaf **45% Overig** bij exact
  diezelfde parameters. Les: tune op de representatie die de pijplijn écht clustert (chunks),
  niet op een goedkopere proxy. De faithful aanpak — chunk-vectoren één keer dumpen en offline
  sweepen met de échte `topics.py`-internals — was wél voorspellend.
- Vastgelegde discover-demo-defaults: **`onderwerp_distance=0.50`, `deelonderwerp_distance=0.42`,
  `min_cluster_size=5`** (in `run.py`). Gekalibreerd op qwen3-embedding; voor de lexicale
  HashingEmbed-default is de afstandsruimte anders en gelden deze waarden niet.

## 3. Kwalitatieve kernbevinding: lexicaal vs. semantisch

Bij gelijke pijplijn en `--no-llm` (TF-IDF-fallbacklabels) is het enige verschil de embedding.

- **Lexicaal** (HashingEmbed / bag-of-words): labels zijn **ruis ongeacht knip-hoogte** —
  TF-IDF grijpt document-ID's en OCR-flarden. Letterlijke voorbeeldlabels:
  `"0425010000000907, kordelaar"` · `"gaat, onder, wel"` · `"rijksweqg, 21dg"` ·
  `"1265308, 150cm, 322143"`. Onbruikbaar als landkaart.
- **Semantisch** (qwen3-embedding:0.6b): labels zijn **herkenbare Woo-onderwerpen**. Letterlijke
  voorbeeldlabels:
  `"rijksweg, aanmeldcentrum, noodopvanglocatie"` · `"amsterdamsestraatweg, perceel,
  omgevingsvergunning"` · `"opvangvoorzieningen, verdeelbesluit, spreiding"` ·
  `"gedoogbeschikking, vergunningverlener, omgevingswet"` · `"saneringsplan, opvragen,
  mijnsteengebieden"` · `"gemeentehuis, bezoekadres, 207"`.

Dit is het bewijs dat de semantische embedding de kwaliteitssprong levert, niet de
LLM-labellaag (die stond uit in beide runs).

## 4. Driver-hardening (Ollama op een groot corpus)

- Ollama's embeddings-endpoint geeft **HTTP 500** op een groot corpus (waargenomen na enkele
  honderden sequentiële calls, en op zeer lange invoer). Eén onbehandelde 500 killt de hele run.
- Fix: **één-retry-plus-nulvector-fallback** per embed. Faalt een call hardnekkig, of geeft het
  model een lege embedding (waargenomen bij lege invoer → dim-0 vector), dan vullen we een
  nulvector van de gangbare dimensie. Lengtes blijven uniform (cosine eist dat) en de clustering
  routeert zo'n document deterministisch naar "Overig" i.p.v. te crashen.

## 5. De Overig-bevinding: precisie boven volledigheid (sterkste materiaal)

Een discover-run liet **45% van de documenten in "Overig"** vallen. De vraag: defect, of de
getrouwe waarheid van een breed gemengd dossier? We bewezen het, in twee stappen.

**Stap 1 — inhoudssteekproef (geen her-embedden):** 25 van de 180 Overig-docs op inhoud bekeken.
~92% bleek herkenbaar bij bestaande onderwerpen te horen (asielopvang, Amsterdamsestraatweg-
vergunningen). Dus: een defect, bewezen met inhoud, niet met gevoel.

**Stap 2 — twee oorzaken gescheiden (faithful chunk-vector-analyse):**

- *Hypothese signaal-verdunning (boilerplate in mailheaders/briefhoofden trekt de embedding weg
  van het thema)* → **VERWORPEN.** De Overig-docs liggen even dicht bij een thema-centroid als de
  geclusterde docs bij hún thema (mediaan-afstand 0,248 vs. geclusterde p90 0,246). **96% van
  Overig ligt <0,45** van een bestaand thema; slechts 1% (2 docs) >0,55. Het collegevoorstel
  noodopvang lag op d=0,117 van het asiel-centroid en zat tóch in Overig. Het semantische signaal
  is intact — géén tekst-schoning nodig.
- *Hypothese parametrisch (te agressieve pooling)* → **BEVESTIGD.** Mechanisme: bij 3 chunks/doc +
  meerderheids-aggregatie + `min_cluster_size=10` belandt een doc waarvan het gemiddelde vlak bij
  een thema ligt tóch in Overig, omdat zijn 3 chunks over sub-clusters <10 versplinteren die
  gepoold worden.

**Het plafond — de fundamentele spanning.** Losser knippen redt Overig-docs terug, maar voorbij
een grens versmelten twee distincte thema's tot één mega-blob (de tegenovergestelde fout: een
kaart die liegt). De sweep-curve (faithful, op de echte chunk-vectoren):

| onderwerp / deel / mcs | #onderwerpen | Overig% | grootste cluster% | gered (van 179) |
|---|---|---|---|---|
| 0.45 / 0.38 / 10 | 7 | 52% | 16% | 3 |
| **0.50 / 0.42 / 5** (demo-default) | **8** | **24%** | **19%** | **91** |
| 0.55 / 0.45 / 3 | 15 | 9% | **50%** ⚠ | 147 |
| 0.60 / 0.50 / 3 | 11 | 4% | **59%** ⚠ | 166 |

**~20–24% Overig is hier de eerlijke bodem:** je krijgt het niet lager zonder distincte thema's
te laten versmelten. Dat is geen tekortkoming maar een **precisie-volledigheid-afweging** — de
tool respecteert de grens van wat eerlijk clusterbaar is in plaats van een mooi getal te forceren.
Een breed gemengd dossier hééft een staart van losse stukken; die in onderwerpen proppen waar ze
niet horen zou een nette landkaart opleveren die liegt.

Tweede hefboom (roadmap, niet nu): meer chunks/doc stabiliseert de meerderheidstoewijzing en kan
de bodem verder verlagen — tegen extra embed-tijd.

## 6. Methodische lessen

- **Ground truth moet onafhankelijk blijven van het systeem-onder-test.** Geen LLM-waarheid
  gebruiken om een LLM-tool te beoordelen; de evaluatie moet uit een andere bron komen.
- **Een getal dat "fout voelt" eerst diagnosticeren, niet wegtunen.** Zie §5: bewijs eerst dát
  het fout is (inhoud), en scheid de mogelijke oorzaken vóór je een fix kiest — parametrisch
  (knip-hoogte) vs. signaal-verdunning (tekst-schoning) vragen verschillende ingrepen.
- **Determinisme ≠ kwaliteit.** HashingEmbed is volledig deterministisch, air-gapped en
  reproduceerbaar — en geeft tegelijk onbruikbare ruislabels. Reproduceerbaarheid is een
  noodzakelijke, geen voldoende eigenschap.
- **Tune op de echte representatie, niet op een goedkope proxy** (zie §2): de doc-vector-sweep
  was 28 procentpunt naast de chunk-niveau-werkelijkheid.

---

# 2026-06-25/26 — Overlap cosine-soeverein vs. cloud-Haiku (proxy-corpus Gooise Meren, 414 PDF's)

Volledig rapport: `runs/cloud-blind-20260625-215625/overlap_report.txt`.

## Overlap cosine-soeverein vs cloud-Haiku (proxy-corpus Gooise Meren, 414 PDF's)
- Setup: identieke query "Woo-verzoek noodopvang asielzoekers", scope-gate off, `score_top_k=0`.
  Cosine-run: qwen3-embedding, `--no-llm`, 346 kandidaten, 89 geselecteerd, 346 unieke
  cosine-waarden. Cloud-run: Voyage-embed + Haiku-selector, 348 kandidaten, 91 geselecteerd.
- Overlap: **54 gedeelde doc-ids. Jaccard 0,429.** Symmetric difference 35 cosine-only / 36
  Haiku-only (+1 funnel-artefact: `1265383.pdf` was geen cosine-kandidaat want qwen3-dedup vouwde
  't als near-dup weg — het was het Woo-verzoek zélf).

## De kernbevinding (dit is waarom de entry bestaat)
- De twee methoden meten **systematisch iets anders, geen ruis**:
  - Cosine koos docs die Haiku op 0,65 zette (net onder cut): docs die het onderwerp **noemen**
    maar er niet over **gaan** ("vermeldt AZC, geen relevante info"; "globale migratiecijfers, geen
    noodopvang-info"). Cosine = vector-nabijheid tot een korte query → vangt lexicale/thematische
    nabijheid, niet inhoudelijke dekking.
  - Haiku koos docs die cosine onder de grens rankte: criteria-dekkende docs (noodopvang-capaciteit,
    Spreidingswet). Haiku = inhoudelijk oordeel over of het doc de zoekvraag behandelt.
- Implicatie: pure cosine op een **korte query** heeft een bekende zwakte — "noemt het maar gaat er
  niet over"-docs scoren hoog. Dit is náást de eerder vastgelegde e-mailmetadata-ruis (adresregels
  die lexicaal dicht bij de query liggen).
- Open hypothese (**niet getest**): een sterker embedding-model (Voyage i.p.v. qwen3:0.6b) met
  dezelfde cosine-selector zou de "noemt-het"-zwakte kunnen verminderen, want beter embedding vangt
  semantische dekking beter dan lexicale nabijheid. Dit is de niet-geteste config B en de eerste
  run-kandidaat voor de echte dataset.

## Tweede signaal (klein, noteren)
- qwen3-dedup vouwde het Woo-verzoek zelf weg als near-duplicate. Mogelijk te agressieve
  near-dup-drempel op het kleine model. Geen demo-blocker; te verifiëren op de echte dataset.

## Harde caveat
- Dit is een **feit over twee verschillende pijplijnen op één proxy-corpus**, geen uitspraak over
  "cosine vs Haiku" geïsoleerd: embedding **én** selector verschillen tegelijk, plus
  truncatie-asymmetrie (Voyage 16000 vs qwen3 8000 chars). De overlap isoleert geen van beide assen.
  **Geen "soeverein ≈ cloud"-conclusie.** En: geldt voor het Gooise Meren-proxy-corpus, niet
  noodzakelijk voor de BZK-dataset.
