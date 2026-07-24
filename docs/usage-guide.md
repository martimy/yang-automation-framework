# Usage Guide

Step-by-step instructions for standing up the lab and working through all
three stages of this repository: discovery scripts, the prototype sketch,
and the full framework. This guide describes what to run and what to expect
— it doesn't reproduce the source code itself; see the linked files for that.

## 1. Prerequisites

Before you start, make sure you have:

- [containerlab](https://containerlab.dev/install/) installed
- Docker running
- Python 3.10 or later
- The Nokia SR Linux container image (containerlab pulls
  `ghcr.io/nokia/srlinux` automatically)
- An Arista cEOS container image, imported yourself as `ceos:image` (Arista
  requires a free account to download this; it isn't publicly redistributable)

## 2. Install Python dependencies

From the repository root:

```bash
pip install -r requirements.txt
```

This installs `ncclient` (NETCONF), `pygnmi` (gNMI), `jinja2` (templating),
`PyYAML`, `python-dotenv`, and `xmltodict`.

Optionally, also install `pyang`, which you'll use in step 4 to inspect YANG
schemas:

```bash
pip install pyang
```

## 3. Deploy the lab topology

```bash
cd topology
sudo containerlab deploy -t yang.clab.yml
```

This brings up two Nokia SR Linux nodes (`srl-01`, `srl-02`) and one Arista
cEOS node (`ceos-01`), wired together per `yang.clab.yml`. `ceos_startup.cfg`
supplies the initial cEOS configuration.

Give the nodes a minute to finish booting before moving on. You can check
their status with:

```bash
sudo containerlab inspect -t yang.clab.yml
```

To tear the lab down later:

```bash
sudo containerlab destroy -t yang.clab.yml
```

## 4. Stage 1 — Discover what each device supports

Before automating anything, look at what the device actually exposes. Work
from the `scripts/` directory for this stage.

1. **List YANG capabilities** — see which models a device advertises over
   NETCONF:

   ```bash
   cd scripts
   python3 get_capabilities.py srl
   python3 get_capabilities.py ceos
   ```

   Pass `srl` or `ceos` as the device argument; the script prints every
   advertised module.

2. **Download a schema** — pull the actual YANG file for a model you're
   interested in, straight from the device:

   ```bash
   python3 get_schema.py srl ietf-interfaces ./
   ```

   Arguments are `<device> <schema name> <output folder>`. This writes
   `ietf-interfaces.yang` into the folder you specify.

3. **Visualize the schema** — once you have a `.yang` file locally, use
   `pyang` to see its structure as a tree:

   ```bash
   pyang -f tree ietf-interfaces.yang
   ```

   Some schemas (like OpenConfig IP addressing) augment another module and
   need it on the search path. Clone the OpenConfig models once:

   ```bash
   git clone https://github.com/openconfig/public openconfig
   pyang -f tree -p openconfig openconfig-if-ip.yang
   ```

4. **Read the current configuration** — see what's already configured on a
   device, in its native XML/JSON form:

   ```bash
   python3 get_configuration.py       # NETCONF, edit the device inside the script if needed
   python3 get_config_gnmi.py         # gNMI equivalent
   ```

5. **Retrieve gNMI capabilities** (parallel to step 1, over gNMI instead of
   NETCONF):

   ```bash
   python3 get_cap_gnmi.py
   ```

6. **Try an XPath filter** — `xpath_support.py` demonstrates filtering a
   `get-config` request with an XPath expression rather than a subtree
   filter:

   ```bash
   python3 xpath_support.py
   ```

7. **Push a configuration payload** — once you've hand-built or generated an
   XML payload, apply it with the safe candidate/validate/commit sequence:

   ```bash
   python3 push_config.py srl path/to/payload.xml
   ```

   Arguments are `<device> <XML file>`. The script uses a candidate
   datastore and validates before committing when the device supports it,
   falling back to a direct merge into the running config otherwise.

See [`lab-exercises.md`](lab-exercises.md) for worked examples of these
commands with real output from the lab, and
[`framework-design-notes.md`](framework-design-notes.md) for how the two
vendors differ in what you'll see.

## 5. Stage 2 — Read the prototype

`prototype/` is a small, illustrative sketch of splitting intent,
orchestration, and translation into separate pieces. It isn't runnable
end-to-end — read it alongside
[`framework-design-notes.md`](framework-design-notes.md) to see the idea
before moving to the real implementation in `framework/`. There's nothing to
execute in this stage; it's a reading step. See `prototype/README.md` for
specifics on what is and isn't runnable there.

## 6. Stage 3 — Run the full framework

1. Set up credentials:

   ```bash
   cd ../framework
   cp .env.example .env
   ```

   The defaults match the lab's default passwords out of the box. See the
   "A note on credentials" section in the top-level `README.md` for a caveat
   about how these values are (and aren't) actually used today.

2. Review `devices.yml` — this is where the device inventory and the
   intended configuration (the "intents") for each device are declared.
   Adjust it if your lab's device names or addresses differ from the
   defaults in `topology/yang.clab.yml`.

3. Run the provisioning tool, choosing a transport:

   ```bash
   python3 deploy.py --transport netconf
   ```

   or

   ```bash
   python3 deploy.py --transport gnmi
   ```

   This reads `devices.yml`, builds the intent objects, hands them to the
   vendor-appropriate orchestrator (which sequences operations correctly —
   see `framework-design-notes.md` for why SR Linux and cEOS need different
   sequences), translates them into vendor-specific payloads, and pushes
   them over the chosen transport.

4. Verify the result using the same discovery techniques from Stage 1 — for
   example, re-run `get_configuration.py` or `get_config_gnmi.py` (adjusted
   to point at the same devices) to confirm the configuration landed as
   intended.

## 7. Stage 4 (optional) — Run the GUI

`gui/` wraps the same `framework/` code from Stage 3 in a local web app —
useful for demoing the pipeline or for editing intents without hand-writing
YAML. It doesn't replace `deploy.py`; it's a second way to drive the same
provisioning logic.

```bash
pip install -r requirements.txt -r gui/backend/requirements.txt
cd gui/backend
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`. Pick a device, click through Intent →
Orchestration → Translation → Transport, and use Deploy the same way you'd
run `deploy.py --transport netconf` (or `gnmi`) — it calls the same
orchestrator code underneath. See [`gui/README.md`](../gui/README.md) for
what each stage shows and a list of current limitations (credential wiring,
a couple of framework-level gaps it deliberately doesn't paper over).

## 8. Extending the framework

To add support for a new feature (for example, BGP) or a new transport
(for example, RESTCONF), see the "Extension Guide" section of
[`framework-developer-guide.md`](framework-developer-guide.md), which lays
out exactly which files to touch and in what order.

## Troubleshooting

- **A script can't connect to a device** — confirm the lab is fully up with
  `sudo containerlab inspect -t topology/yang.clab.yml`, and that you're
  using the right port (830 for NETCONF, 57400 for SR Linux gNMI, 6030 for
  cEOS gNMI, per the values hardcoded in the scripts).
- **`get_schema.py` fails on a model name** — re-run `get_capabilities.py`
  first; the exact module name it prints is what `get_schema.py` expects.
- **A `push_config.py` payload is rejected** — check that the XML matches
  the schema you retrieved in step 4.2; also confirm the device advertised
  `:candidate` and `:validate` capabilities if you're relying on that
  safety sequence.
