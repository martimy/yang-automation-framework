# Model-Driven Network Configuration: NETCONF, gNMI, and YANG

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

**Known inconsistency:** `deploy.py` loads these values from `.env` into a
`passwords` dict, but `transport/netconf.py` and `transport/gnmi.py` don't
actually read it — they hardcode the same lab-default credentials directly
in their own `devices` mappings. So today, changing `.env` alone won't
change what credentials are used; you'd also need to edit those two files
(or wire `passwords` through to them). The standalone scripts in `scripts/`
and `prototype/` hardcode the same defaults too, for simplicity. Don't reuse
any of these default credentials outside of this isolated lab.

## License

MIT — see [LICENSE](LICENSE).
