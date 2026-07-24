# GUI

A local web app for `framework/`: visualize the intent → orchestration →
translation → transport pipeline per device, author/edit intents, and
trigger deployment — without leaving the browser.

It's a second consumer of `framework/`, not a rewrite of it. The backend
imports `framework/`'s own modules directly (`intent.*`, `orchestration.*`,
`translation.*`, `transport.*`, `registry`) the same way `deploy.py` does,
so there is exactly one implementation of what a device's intents mean —
the GUI can't drift from the CLI because it doesn't have its own copy of
that logic.

## Running it

```bash
pip install -r requirements.txt -r gui/backend/requirements.txt
cd gui/backend
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000`. This serves both the API (`/api/*`) and
the frontend from one process — nothing else to stand up.

## What each pipeline stage does

| Stage | What you see | Editable? |
|---|---|---|
| **Intent** | The selected device's entry from `devices.yml`, as a generated form or raw YAML | Yes — both views write back to `devices.yml` |
| **Orchestration** | Which orchestrator class applies to the device's vendor, and its fixed phase order | No — one orchestrator per vendor today, nothing to choose between yet |
| **Translation** | The exact NETCONF XML / gNMI JSON each intent renders to, via `translator.translate()` | Preview only — calls translators directly, never `transport.push_config()`, so clicking around never touches a real device |
| **Transport** | Deploy: runs the real `orchestrator.bootstrap()` + `.provision()` against the chosen transport | Triggers a real push, with a confirm dialog first |

The Intent form is generated from the framework's own dataclasses
(`dataclasses.fields()` introspection in `gui/backend/services/schema.py`),
not hand-written per field — it won't drift if a field is added to
`intent/*.py`. Which categories a device's form offers (e.g. no Network
Instances for cEOS) comes from `registry.py`'s `TRANSLATORS` map, not a
hardcoded vendor list.

## Known limitations

- **Credentials aren't wired through.** This is inherited from
  `framework/`, not introduced by the GUI — see "A note on credentials" in
  the top-level `README.md`. Whatever you enter doesn't yet reach
  `transport/netconf.py` / `transport/gnmi.py`.
- **Saving through the GUI makes `devices.yml` more verbose.** Fields
  omitted in a hand-written entry because they matched a dataclass default
  (`enabled: true`, `area_type: normal`, etc.) get written out explicitly
  after any save via the GUI. Functionally identical, just a noisier diff.
- **Fields typed `str` are saved as strings.** `schema.py` reports each
  field's *declared* type, not the type of whatever value happens to be in
  `devices.yml` today. OSPF's `name` field is typed `str` but some entries
  use a bare number (`name: 100`) — editing that field through the form
  saves it back as `"100"`. Harmless for NETCONF/XML; check before relying
  on it for a gNMI/JSON payload that expects a number.
- **Intent types with no framework backing are preserved, not supported.**
  If `devices.yml` has a `protocols` key (or any top-level key) the
  framework has no dataclass/translator for — e.g. a hand-added `snmp:`
  block — the GUI keeps it byte-for-byte through every save/load and flags
  it with a warning banner, but it is never translated or deployed. Adding
  real support means the framework-level work described in "To add a new
  Feature" in `docs/framework-developer-guide.md`; only then will
  `registry.py` pick it up and the GUI stop treating it as inert.
- **`intent/ni_interface.py` and `translation/ceos/global_routing.py` are
  excluded on purpose.** Neither is reachable from `registry.py` — the
  first has a broken import, the second is unregistered — so they were
  left out of the schema and translation preview rather than papered over.
  See the "Extension Guide" note below if that ever changes.

## If you extend the framework

The GUI derives everything from `registry.py` and the `intent/*.py`
dataclasses, not by scanning every file in `framework/`. Concretely, that
means when you follow the "To add a new Feature" steps in
`docs/framework-developer-guide.md`:

- A new intent dataclass is picked up by the Intent form automatically
  once it's added to `INTENT_CLASSES` in `gui/backend/services/schema.py`.
- A new translator only shows up in the Translation preview
  (`preview_translation()` in `gui/backend/services/pipeline.py`) once
  there's an explicit call for it there — mirror whatever the vendor's
  orchestrator actually does in `orchestration/<vendor>.py`, including any
  secondary payload the way SR Linux's `ni_interface` binding is handled
  alongside `subinterface`.
- Registering a translator in `registry.py` is what makes
  `supported_intent_categories()` in `schema.py` show or hide it per
  vendor — nothing else to update there.
