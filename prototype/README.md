# Prototype

This is the minimal sketch that motivates the full `framework/` design: a
first pass at splitting intent, orchestration, and translation into separate
pieces.

**These files are illustrative, not runnable as a package.** `orchestrator.py`
in particular references intent classes (`GlobalRoutingIntent`,
`NetworkInstanceIntent`, `NiInterfaceBindingIntent`) that aren't defined here
— they exist in the real form in `framework/intent/`. Read this directory to
see the shape of the idea; run `framework/` to see it working end-to-end.
