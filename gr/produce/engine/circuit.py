"""Draws an episode's circuit DSL with schemdraw and writes an SVG.

    python circuit.py <spec.json> <out.svg> [ink] [accent]

spec = [[element, direction, label], ...]; elements chain end-to-start.
"""
import json
import sys

import schemdraw
import schemdraw.elements as elm

schemdraw.use("svg")
INK = sys.argv[3] if len(sys.argv) > 3 else "#111827"
ACCENT = sys.argv[4] if len(sys.argv) > 4 else "#B45309"

ELEMENTS = {
    "SourceV": elm.SourceV,
    "SourceSin": elm.SourceSin,
    "Battery": elm.Battery,
    "Resistor": elm.Resistor,
    "Capacitor": elm.Capacitor,
    "Inductor": elm.Inductor2,
    "Lamp": elm.Lamp,
    "Switch": elm.Switch,
    "Fuse": elm.Fuse,
    "Diode": elm.Diode,
    "LED": elm.LED,
    "Ground": elm.Ground,
    "Line": elm.Line,
    "Dot": elm.Dot,
    "Motor": elm.Motor,
    "Transformer": elm.Transformer,
    "Meter_V": elm.MeterV,
    "Meter_A": elm.MeterA,
    "Heater": elm.Resistor,  # drawn as a resistor (a heating element is one)
}


def main(spec_path, out_path):
    spec = json.load(open(spec_path, encoding="utf8"))
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=3, fontsize=15, color=INK, lw=2.6, font="Arial")
        for name, direction, label in spec:
            cls = ELEMENTS.get(name)
            if cls is None:
                raise SystemExit(f"unknown element {name}")
            e = cls()
            if name in ("Dot", "Ground"):
                d.add(e)
                continue
            if name == "Transformer":
                d.add(e.label(label, loc="top") if label else e)
                continue
            e = getattr(e, direction)()
            if label:
                e = e.label(label, color=ACCENT if name != "Line" else INK)
            d.add(e)
        d.save(out_path, transparent=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
