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
- **SNMP is supported for SR Linux, not cEOS.** SR Linux has a registered
  translator (`registry.py`'s `TRANSLATORS["srlinux"]["snmp"]`), so
  `supported_intent_categories("srlinux")` includes `snmp`, the Intent
  form offers it, and Deploy pushes it. cEOS has none, because SNMP can't
  be configured via YANG on cEOS — `supported_intent_categories("ceos")`
  correctly never includes it, and `orchestration/ceos.py` has no
  `configure_snmp()` to call. This is a real per-vendor difference, not a
  gap to fill in.
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
means when you follow the checklist in `docs/framework-developer-guide.md`'s
"Extension Guide":

- **Decide the same two things the checklist calls out first, and make
  the GUI agree with `devices.yml`/`deploy.py` about them** — whether the
  new key is top-level or nested under `protocols`, and whether it's a
  single instance or a list per device. The GUI doesn't infer this;
  `gui/backend/services/pipeline.py`'s `hydrate_intents()` /
  `dehydrate_intents()` need the exact same top-level-vs-`protocols` and
  single-vs-list handling as `deploy.py`'s own `hydrate_intents()`
  (tracked via `KNOWN_TOP_LEVEL_INTENT_KEYS` / `KNOWN_PROTOCOL_KEYS`), or
  the GUI silently disagrees with the CLI about the data's shape — see the
  SNMP changelog entry below for what that looks like in practice.
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
- In `gui/frontend/index.html`, a single-instance category needs a form
  block mirroring `ntp`'s (or `snmp`'s); a list-shaped one needs adding to
  `listCategories` instead. Neither happens automatically.

Once you've made these changes, run `python3 gui/backend/check_consistency.py`
from the repo root. It re-derives what `registry.py`/`scope.py` imply the
GUI should look like and compares that against what `pipeline.py`/
`schema.py` actually do — the exact mismatch SNMP had, below, would have
been caught by this in seconds instead of surfacing as a silent no-op
deploy. Exits `0`/`OK` if everything agrees, `1` with a specific
explanation of what to fix if not.

**Changelog — SNMP shape mismatch (fixed):** the first pass at SNMP only
added `intent/snmp.py` and registered it in `schema.py`'s `INTENT_CLASSES`.
`pipeline.py` hydrated/dehydrated it as a *list nested under `protocols`*,
matching `ospf`'s shape — but `devices.yml`/`deploy.py`/`scope.py` all
treat SNMP as a *single top-level dict*, since it isn't a routing
protocol. Neither side raised an error: a real `deploy.py --categories
snmp` run worked, but the GUI's Translation preview showed no SNMP
payload at all, and deploying SNMP from the GUI silently did nothing
(`orchestrator.provision()` never found `intents["snmp"]`, since the GUI
had it nested one level down from where `provision()` looks). All three
GUI files now match the framework's shape for `snmp`.
