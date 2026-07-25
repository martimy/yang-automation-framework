# Multivendor YANG Automation Framework

A hands-on tutorial and reference framework for model-driven network
automation across multiple vendors, built on a Nokia SR Linux + Arista cEOS
lab deployed with [containerlab](https://containerlab.dev/).

It progresses through three stages, each in its own directory:

1. **`scripts/`** — small, standalone NETCONF/gNMI scripts for *discovering*
   what a device supports (capabilities, schemas, config) before writing any
   automation.
2. **`prototype/`** — a minimal, single-file sketch of an intent /
   orchestration / translation / transport split. Illustrative, not meant to
   run as-is.
3. **`framework/`** — a working, multi-file provisioning tool that
   implements that split for real, across NETCONF and gNMI, for both
   vendors.

An optional **`gui/`** — a local web app for visualizing and driving
`framework/` from a browser — sits on top of stage 3; see
[`gui/README.md`](gui/README.md).

See [`Introduction.md`](Introduction.md) for the motivation and architecture
in more depth.

## Repository layout

```text
.
├── Introduction.md               # Why this tutorial exists, and its architecture
├── docs/
│   ├── usage-guide.md             # Step-by-step: setup, running, extending
│   ├── lab-exercises.md           # Worked examples: commands + captured output
│   ├── framework-design-notes.md # Vendor differences, model choices, gotchas
│   └── framework-developer-guide.md
├── topology/
│   ├── yang.clab.yml             # containerlab topology (2x SR Linux, 1x cEOS)
│   └── ceos_startup.cfg
├── scripts/                      # Stage 1: discovery scripts (NETCONF + gNMI)
├── prototype/                    # Stage 2: minimal intent/orchestrator/translator sketch
├── framework/                    # Stage 3: the full provisioning tool
├── gui/                           # Optional: local web app for the framework (see gui/README.md)
├── requirements.txt
└── LICENSE
```

## Prerequisites

- [containerlab](https://containerlab.dev/install/)
- Docker
- A Nokia SR Linux container image (`ghcr.io/nokia/srlinux`, pulled automatically)
- An Arista cEOS container image — **you must obtain this yourself** from
  Arista (requires an Arista account) and import it as `ceos:image`, or set
  the `CEOS_IMAGE` environment variable to whatever tag you import it as
- Python 3.10+

## Getting started

See [`docs/usage-guide.md`](docs/usage-guide.md) for full step-by-step
instructions covering the lab, all three stages, and troubleshooting. In
short:

```bash
pip install -r requirements.txt
cd topology && sudo containerlab deploy -t yang.clab.yml
```

Then work through `scripts/` (discovery), `prototype/` (read-only sketch),
and `framework/` (the full tool) in that order.

## GUI (optional)

Once `framework/` is set up, `gui/` gives you a local web app for the same
pipeline — visualize intent → orchestration → translation → transport per
device, edit intents in a form or raw YAML, and trigger deployment from a
browser instead of the CLI. It's a second consumer of `framework/`'s own
code, not a separate implementation. See [`gui/README.md`](gui/README.md)
for setup and a frank list of what's implemented vs. not yet.

## A note on credentials

`framework/.env.example` documents the lab's default credentials
(`admin`/`admin` for cEOS, `admin`/`NokiaSrl1!` for SR Linux) — these are the
well-known vendor/containerlab defaults for local sandboxes, not secrets.
Copy it to `.env` (already gitignored) rather than committing real
credentials if you change them.

`.env` only ever holds the password itself, by environment variable name.
Everything else about how to connect to a device — its vendor, its
username, and which `.env` variable holds its password — is declared in
`framework/inventory.yml`, with per-vendor defaults and optional per-host
overrides. `credentials.py` resolves the two together and fails loudly
(a clear, specific error) if a host isn't listed in `inventory.yml` or its
password variable isn't set — there's no hardcoded fallback, by design.
`deploy.py` and the GUI both go through this same resolution, so there's
one place this logic lives, not several.

The standalone scripts in `scripts/` and `prototype/` hardcode the lab
defaults directly, for simplicity — they predate `inventory.yml` and are
meant to stay minimal illustrations, not full framework consumers. Don't
reuse any of these default credentials outside of this isolated lab.

## License

MIT — see [LICENSE](LICENSE).
