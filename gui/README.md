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
| **Transport** | Deploy: runs the real `orchestrator.bootstrap()` + `.provision()` against the chosen transport, for a chosen subset of intent categories | Triggers a real push, with a confirm dialog first. Credentials are resolved via `credentials.py` (`inventory.yml` + `.env`) — nothing hardcoded, and it fails loudly rather than guessing if a host or password is missing. A checkbox list lets you deploy only some categories (e.g. just `snmp`) instead of everything configured for the device, mirroring `deploy.py --categories`. |

The Intent form is generated from the framework's own dataclasses
(`dataclasses.fields()` introspection in `gui/backend/services/schema.py`),
not hand-written per field — it won't drift if a field is added to
`intent/*.py`. Which categories a device's form offers (e.g. no Network
Instances for cEOS) comes from `registry.py`'s `TRANSLATORS` map, not a
hardcoded vendor list.

## Known limitations

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
- **SNMP has a dataclass and GUI plumbing, but no translator yet.**
  `intent/snmp.py`'s `SnmpIntent` hydrates/dehydrates correctly and shows
  up in the Intent form's schema, but no vendor has an `snmp` translator
  registered in `registry.py`, so `supported_intent_categories()` never
  shows it for any device and nothing ever gets deployed for it. Data you
  enter is preserved safely across saves either way — this is a "not built
  yet," not a "will be silently lost" situation.
- **Intent types with no framework backing at all are preserved, not
  supported.** If `devices.yml` has a key the framework has no
  dataclass for whatsoever — not even a partial one like SNMP — the GUI
  keeps it byte-for-byte through every save/load and flags it with a
  warning banner, but it is never translated or deployed. Adding real
  support means the framework-level work described in "To add a new
  Feature" in `docs/framework-developer-guide.md`.
- **`translation/ceos/global_routing.py` is excluded on purpose.** It's
  unregistered in `registry.py`, so it was left out of the schema and
  translation preview rather than papered over. (`intent/ni_interface.py`
  used to be in the same boat but has since been removed from the
  framework entirely.) See the "Extension Guide" note below if that ever
  changes.
- **No GUI for `inventory.yml` or credentials.** Which devices exist and
  how to connect to them is edited by hand in `framework/inventory.yml`
  and `framework/.env` — the GUI reads through `credentials.py` when you
  hit Deploy, but doesn't expose a way to view or edit that file. Worth
  building if device-list changes become a common student task; not
  built yet.

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
