# HACKATHON-STAND — bevroren 2026-06-25 (nacht)

> Oriëntatienota voor morgen. Untracked bestand in repo-root, bewust **niet** gecommit
> naar welke branch dan ook. Verwijderen mag zodra je weer op stoom bent.

## Branch-stand (geverifieerd vannacht)

| Branch | Commit | Wat het is |
|---|---|---|
| `main` | `88819f9` | **MVP-fallback, onaangeroerd.** LLM-relevantie-selector. qwen3:0.6b ongeschikt; Haiku wél geschikt. |
| `change/converge-final-flow` | `6af8334` | **Demo-kandidaat.** Cosine-selector + RemoteDisconnected-fix + scope-gate. Option-a-knop (`ZEEF_SCOPE_FILTER_LLM`, default-on) staat nu **op de branch** — zelfstandig draaibaar. Bewezen op het echte corpus (346 unieke waarden, asiel-docs hoog, **gate-off vereist**). |
| `change/voyage-transport-hardening` | `f4ed1b0` | **Cloud-pad** (Voyage + Haiku). Truncatie + batching + bounded retry/back-off (429/5xx). Patch + tests + OpenSpec gecommit. Live bewezen; key heeft tegoed. |

Overige branches (discover-mode, output-hygiene, pdf-validity-gate, topic-clustering,
viewer-ui) ongewijzigd in hun eigen worktrees.

## Wat vannacht is gebeurd
- Geverifieerd dat de option-a scope-filter-knop (`scope_filter_llm` in config.py,
  doorgedraad cli → run → scope_filter met `scope_llm=`) volledig op
  `change/converge-final-flow` @6af8334 staat. config.py en scope_filter.py byte-identiek
  aan de wegwerp-worktree; enige verschil = ingekorte comments in run.py/cli.py (bewust).
- Wegwerp-worktree (`zeef-main-wt` op main, met losse option-a-edits) opgeruimd **nadat**
  bevestigd was dat de edits veilig op de branch staan.
- **Niets naar main. Geen merge. Geen push.** Alles lokaal.

## Open beslissingen voor morgen
1. **Welke config gaat de demo in?**
   - cosine + qwen3 (soeverein, lokaal)
   - cosine + Voyage (cloud) — **NIET getest**
   - Haiku LLM-selector (main-fallback)
2. **Merge-beslissingen** — welke branch(es) naar main, in welke volgorde.
3. **cosine + Voyage-embedding** is de niet-geteste, mogelijk-beste config. Overweeg
   eerst te testen vóór de demo-keuze.

## Vaste werkwijze morgen
- Query komt van **buiten** (BZK levert 'm) — niet uit de data afleiden.
- **Scope-gate UIT** bij de cosine-flow (`ZEEF_SCOPE_FILTER_LLM=0` / `scope_filter_llm=False`).
- Top-N met **eigen ogen** nalopen op ruis vóór tonen.
