## Context

`pipeline/score.py` scores the top-K reranked candidates with one LLM call each. The prompt asks
for two lines:

```
SCORE: 80
MOTIVATIE: bevat zowel de publicatie- als de geheimhoudingsclausule ...
```

and `_parse` scrapes them with `_SCORE_RE` / `_MOTIVE_RE`, mapping the score to 0..1
(`llm_relevance` and `final`) and the rationale to `Document.rationale`. No match on the score
line → `(0.0, raw_answer[:200])`. The behaviour to protect: 0..1 range, top-K demotion of the
rest, unparseable → 0.0 with the raw text kept, never crash, `--no-llm` skips the stage entirely,
and a per-document audit event with the exact prompt, model and location.

Two backends can do better than scraping: Claude (tool-use with `input_schema`) and Ollama
(`format` JSON schema on `/api/generate`). Where structured output is reliable we should use it;
where it is not, regex stays.

## Goals / Non-Goals

**Goals:**
- Guaranteed-parseable score + rationale where the backend supports structured output.
- Keep the regex path as an explicit, tested fallback for backends without reliable JSON mode.
- Make "why did this backend take the JSON route" readable without tracing code.
- Make the JSON path at least as auditable as the regex path it replaces.

**Non-Goals:**
- Touching `LLMProvider.complete` or the other `complete()` callers (criteria, summarise,
  scope-filter, topic-labels).
- Structured output for stages other than scoring.
- Live cloud testing, changing the 0..1 score semantics, or changing selection.

## Decisions

### D-CAPABILITY — an explicit `StructuredLLMProvider` protocol, not `hasattr` dispatch
Rather than probe `hasattr(llm, "complete_json")` at the call site, declare the capability as a
`runtime_checkable` protocol in `protocols.py`:

```
@runtime_checkable
class StructuredLLMProvider(Protocol):
    name: str
    location: str
    def complete_json(self, prompt: str, schema: dict, *, system: str | None = None) -> dict | None: ...
```

`score.py` branches on `isinstance(llm, StructuredLLMProvider)`. This is the same
duck-typing under the hood, but the intent is named and inspectable: the reason a backend takes
the JSON route is "it satisfies `StructuredLLMProvider`", visible in one place. `LLMProvider`
stays exactly as it is — `complete_json` is a *separate*, additive protocol, so existing providers
(and `NullLLM`) remain valid `LLMProvider`s without implementing anything new.

`complete_json` returns `None` (or raises, caught by the caller) when the backend tried structured
output and could not produce a valid object — that signals "fall back", distinct from a valid
`{score: 0}`.

### D-SCHEMA — one fixed schema, shared by both backends
A single JSON schema describes the expected object:

```
{"type": "object",
 "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 100},
                "motivatie": {"type": "string"}},
 "required": ["score", "motivatie"]}
```

- Claude: passed as a tool `input_schema`; the model is forced to call the tool (temperature 0),
  and `complete_json` returns the tool input dict.
- Ollama: passed as `format` on `/api/generate` (Ollama accepts a JSON schema there);
  `complete_json` parses `response` as JSON.

The score is clamped to 0..100 then ÷100 (identical to the regex path), so the 0..1 contract is
enforced regardless of which path produced the number.

### D-DEGRADE — three explicit tiers, never worse than today
1. **Structured** — `isinstance(llm, StructuredLLMProvider)`: call `complete_json`. If it returns
   a valid dict, use `score`/`motivatie`.
2. **Regex** — backend is not structured, or `complete_json` returned `None`/raised, or the dict
   was missing/invalid fields: fall back to a `complete()` free-text call parsed by the existing
   `_SCORE_RE`/`_MOTIVE_RE`.
3. **Score-0** — regex also fails to find a score: `(0.0, raw_answer)` exactly as today.

Tier 3 is the current behaviour; tiers 1–2 only ever *improve* parseability. Nothing crashes.

### D-AUDIT — the JSON path logs schema + raw structured response
The regex path logs the exact prompt. The JSON path is at risk of being *less* auditable (the
"prompt" alone doesn't show what shape was demanded or what the model actually returned). So the
score event on the JSON path additionally records:
- `schema`: the JSON schema sent to the backend,
- `raw_structured`: the raw structured object the backend returned (before clamping/normalisation),
alongside the existing `prompt`, `model`, `location`, `relevance`, `rationale`. The regex path
keeps logging the free-text answer as today. This keeps the new path at least as traceable as the
one it replaces.

### D-NOLLM — unchanged
`--no-llm` still short-circuits the stage (`score.py:48`); `NullLLM` implements neither
`complete_json` nor any new method and is never reached here. The deterministic, air-gapped run is
untouched.

## Risks / Trade-offs

- **Ollama JSON reliability varies by model/version.** Mitigation: `complete_json` validates the
  returned object against the required fields; any miss returns `None` → regex fallback. A backend
  is only ever opted *in* by satisfying `StructuredLLMProvider`; if a deployment has an
  unreliable model, the per-backend opt-out (a `config.py` flag) can force the regex path. Default
  is structured-where-supported.
- **Prompt drift in the audit trail.** The structured prompt differs from the `SCORE:/MOTIVATIE:`
  text prompt; the audit-log records the exact (changed) prompt, plus schema and raw response, so
  the trail is fully reconstructable. Noted in the CHANGELOG.
- **Cloud not live-tested.** The `ClaudeLLM.complete_json` tool-use path is wired and covered by a
  fake, not by a live key (open question Q3). Documented; no behavioural claim about live cloud.

## Migration

None. No data or config migration. Default behaviour changes only for backends that satisfy
`StructuredLLMProvider` (they now get guaranteed-parseable scores); all other backends behave
exactly as today. `--no-llm` is identical.
