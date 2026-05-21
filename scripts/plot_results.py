"""Create SVG plots from the simulated or measured charge log CSV.

The script intentionally uses only the Python standard library. That keeps the
project reproducible on a fresh machine and still produces clean plots for the
README and GitHub Pages.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "simulated_charge_log.csv"
PLOT_DIRS = [ROOT / "plots", ROOT / "docs" / "assets" / "plots"]
WIDTH = 1000
HEIGHT = 520
PADDING = {"left": 84, "right": 32, "top": 74, "bottom": 70}
COLORS = {
    "blue": "#2454a6",
    "green": "#23845b",
    "orange": "#cc6b1f",
    "red": "#b3261e",
    "gray": "#58616d",
    "grid": "#d8dee9",
    "ink": "#17202a",
    "muted": "#58616d",
    "paper": "#ffffff",
    "panel": "#f6f8fb",
}


def read_rows(path: Path) -> dict[str, list[float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        raise ValueError(f"No rows found in {path}")

    def series(name: str) -> list[float]:
        return [float(row[name]) for row in rows]

    return {
        "elapsed_min": series("elapsed_min"),
        "voltage": series("cell_voltage_v"),
        "current": series("charge_current_mA"),
        "temperature": series("temperature_c"),
        "relay": series("relay_state"),
        "soc": series("soc_percent"),
        "low": series("setpoint_low_v"),
        "high": series("setpoint_high_v"),
        "pid_setpoint": series("pid_setpoint_v"),
        "voltage_error": series("voltage_error_v"),
        "pid_p": series("pid_p_percent"),
        "pid_i": series("pid_i_percent"),
        "pid_d": series("pid_d_percent"),
        "pid_output": series("pid_output_percent"),
        "pid_relay_request": series("pid_relay_request"),
        "temp_cutoff": series("temperature_cutoff_c"),
    }


def points_to_path(points: Iterable[tuple[float, float]]) -> str:
    iterator = iter(points)
    first = next(iterator)
    chunks = [f"M {first[0]:.2f} {first[1]:.2f}"]
    chunks.extend(f"L {x:.2f} {y:.2f}" for x, y in iterator)
    return " ".join(chunks)


def step_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    path = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for (prev_x, prev_y), (x, y) in zip(points, points[1:]):
        path.append(f"L {x:.2f} {prev_y:.2f}")
        path.append(f"L {x:.2f} {y:.2f}")
    return " ".join(path)


def scale(value: float, source_min: float, source_max: float, target_min: float, target_max: float) -> float:
    if source_max == source_min:
        return (target_min + target_max) / 2
    ratio = (value - source_min) / (source_max - source_min)
    return target_min + ratio * (target_max - target_min)


def write_all(filename: str, svg: str) -> None:
    for directory in PLOT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_text(svg, encoding="utf-8")


def render_plot(
    *,
    title: str,
    ylabel: str,
    x: list[float],
    series: list[dict[str, object]],
    filename: str,
    y_min: float | None = None,
    y_max: float | None = None,
    bands: list[dict[str, object]] | None = None,
    hlines: list[dict[str, object]] | None = None,
    y_tick_labels: dict[float, str] | None = None,
) -> None:
    bands = bands or []
    hlines = hlines or []
    all_values: list[float] = []
    for item in series:
        all_values.extend(float(v) for v in item["values"])  # type: ignore[index]
    for item in hlines:
        all_values.append(float(item["value"]))
    for band in bands:
        all_values.extend(float(v) for v in band["low"])  # type: ignore[index]
        all_values.extend(float(v) for v in band["high"])  # type: ignore[index]

    explicit_y_min = y_min is not None
    explicit_y_max = y_max is not None
    y_min = min(all_values) if y_min is None else y_min
    y_max = max(all_values) if y_max is None else y_max
    margin = (y_max - y_min) * 0.08 if y_max > y_min else 1
    if not explicit_y_min:
        y_min -= margin
    if not explicit_y_max:
        y_max += margin

    plot_left = PADDING["left"]
    plot_right = WIDTH - PADDING["right"]
    plot_top = PADDING["top"]
    plot_bottom = HEIGHT - PADDING["bottom"]
    x_min, x_max = min(x), max(x)

    def sx(value: float) -> float:
        return scale(value, x_min, x_max, plot_left, plot_right)

    def sy(value: float) -> float:
        return scale(value, y_min, y_max, plot_bottom, plot_top)

    x_ticks = [x_min + (x_max - x_min) * index / 6 for index in range(7)]
    y_ticks = sorted(y_tick_labels.keys()) if y_tick_labels else [y_min + (y_max - y_min) * index / 5 for index in range(6)]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        f"<title id=\"title\">{html.escape(title)}</title>",
        f"<desc id=\"desc\">{html.escape(title)}: {html.escape(ylabel)} ueber Zeit.</desc>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{COLORS["paper"]}"/>',
        f'<rect x="{plot_left}" y="{plot_top}" width="{plot_right - plot_left}" height="{plot_bottom - plot_top}" fill="{COLORS["panel"]}" stroke="{COLORS["grid"]}"/>',
        f'<text x="{plot_left}" y="38" font-family="Arial, sans-serif" font-size="25" font-weight="700" fill="{COLORS["ink"]}">{html.escape(title)}</text>',
        f'<text x="{plot_left}" y="{HEIGHT - 22}" font-family="Arial, sans-serif" font-size="15" fill="{COLORS["muted"]}">Zeit [min]</text>',
        f'<text x="24" y="{plot_top + 18}" font-family="Arial, sans-serif" font-size="15" fill="{COLORS["muted"]}" transform="rotate(-90 24 {plot_top + 18})">{html.escape(ylabel)}</text>',
    ]

    for tick in x_ticks:
        px = sx(tick)
        parts.append(f'<line x1="{px:.2f}" y1="{plot_top}" x2="{px:.2f}" y2="{plot_bottom}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        parts.append(f'<text x="{px:.2f}" y="{plot_bottom + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="{COLORS["muted"]}">{tick:.0f}</text>')
    for tick in y_ticks:
        py = sy(tick)
        label = y_tick_labels.get(tick, f"{tick:.2f}") if y_tick_labels else f"{tick:.2f}"
        parts.append(f'<line x1="{plot_left}" y1="{py:.2f}" x2="{plot_right}" y2="{py:.2f}" stroke="{COLORS["grid"]}" stroke-width="1"/>')
        parts.append(f'<text x="{plot_left - 12}" y="{py + 4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="{COLORS["muted"]}">{html.escape(label)}</text>')

    for band in bands:
        low = [float(v) for v in band["low"]]  # type: ignore[index]
        high = [float(v) for v in band["high"]]  # type: ignore[index]
        upper = [(sx(xv), sy(yv)) for xv, yv in zip(x, high)]
        lower = [(sx(xv), sy(yv)) for xv, yv in reversed(list(zip(x, low)))]
        path = points_to_path(upper + lower) + " Z"
        parts.append(f'<path d="{path}" fill="{band["color"]}" opacity="{band.get("opacity", 0.35)}"/>')

    legend_x = plot_left
    legend_y = 58
    for item in series:
        values = [float(v) for v in item["values"]]  # type: ignore[index]
        coords = [(sx(xv), sy(yv)) for xv, yv in zip(x, values)]
        path = step_path(coords) if item.get("step") else points_to_path(coords)
        parts.append(
            f'<path d="{path}" fill="none" stroke="{item["color"]}" stroke-width="{item.get("width", 3)}" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        parts.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 26}" y2="{legend_y}" stroke="{item["color"]}" stroke-width="4" stroke-linecap="round"/>')
        parts.append(f'<text x="{legend_x + 34}" y="{legend_y + 5}" font-family="Arial, sans-serif" font-size="13" fill="{COLORS["muted"]}">{html.escape(str(item["label"]))}</text>')
        legend_x += 170

    for item in hlines:
        py = sy(float(item["value"]))
        parts.append(
            f'<line x1="{plot_left}" y1="{py:.2f}" x2="{plot_right}" y2="{py:.2f}" stroke="{item["color"]}" stroke-width="2" stroke-dasharray="8 7"/>'
        )
        parts.append(f'<text x="{plot_right - 8}" y="{py - 8:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="13" fill="{item["color"]}">{html.escape(str(item["label"]))}</text>')

    parts.append("</svg>")
    write_all(filename, "\n".join(parts))


def make_plots(data: dict[str, list[float]]) -> None:
    t = data["elapsed_min"]
    render_plot(
        title="Spannung ueber Zeit",
        ylabel="Spannung [V]",
        x=t,
        series=[{"label": "Zellspannung", "values": data["voltage"], "color": COLORS["blue"]}],
        bands=[{"low": data["low"], "high": data["high"], "color": "#e6f0ec", "opacity": 0.85}],
        hlines=[
            {"value": data["low"][0], "label": "Ein 3,85 V", "color": COLORS["green"]},
            {"value": data["high"][0], "label": "Aus 4,00 V", "color": COLORS["orange"]},
        ],
        filename="voltage_over_time.svg",
    )

    render_plot(
        title="Strom ueber Zeit",
        ylabel="Ladestrom [mA]",
        x=t,
        y_min=0,
        series=[{"label": "Ladestrom", "values": data["current"], "color": COLORS["orange"]}],
        filename="current_over_time.svg",
    )

    render_plot(
        title="Temperatur ueber Zeit",
        ylabel="Temperatur [Grad C]",
        x=t,
        series=[{"label": "Zelltemperatur", "values": data["temperature"], "color": COLORS["red"]}],
        hlines=[{"value": data["temp_cutoff"][0], "label": "Notabschaltung", "color": COLORS["gray"]}],
        filename="temperature_over_time.svg",
    )

    render_plot(
        title="Relaiszustand ueber Zeit",
        ylabel="Relais",
        x=t,
        y_min=0,
        y_max=1,
        y_tick_labels={0: "Aus", 1: "Ein"},
        series=[{"label": "Relais", "values": data["relay"], "color": COLORS["green"], "step": True}],
        filename="relay_state_over_time.svg",
    )

    render_plot(
        title="Vergleich Sollbereich und Istwert",
        ylabel="Spannung [V]",
        x=t,
        series=[
            {"label": "Istwert", "values": data["voltage"], "color": COLORS["blue"]},
            {"label": "unterer Schaltpunkt", "values": data["low"], "color": COLORS["green"], "width": 2},
            {"label": "oberer Schaltpunkt", "values": data["high"], "color": COLORS["orange"], "width": 2},
        ],
        bands=[{"low": data["low"], "high": data["high"], "color": "#f5eadf", "opacity": 0.8}],
        filename="setpoint_vs_actual.svg",
    )

    render_plot(
        title="PID-Referenzausgang",
        ylabel="Ausgang [%]",
        x=t,
        y_min=0,
        y_max=100,
        series=[
            {"label": "u_PID", "values": data["pid_output"], "color": COLORS["blue"]},
            {
                "label": "Relais real",
                "values": [value * 100.0 for value in data["relay"]],
                "color": COLORS["green"],
                "step": True,
                "width": 2,
            },
            {
                "label": "PID Schwelle",
                "values": [value * 100.0 for value in data["pid_relay_request"]],
                "color": COLORS["orange"],
                "step": True,
                "width": 2,
            },
        ],
        hlines=[{"value": 50.0, "label": "50 Prozent", "color": COLORS["gray"]}],
        filename="pid_reference_output.svg",
    )

    render_plot(
        title="PID-Anteile",
        ylabel="Anteil [%]",
        x=t,
        series=[
            {"label": "P-Anteil", "values": data["pid_p"], "color": COLORS["blue"]},
            {"label": "I-Anteil", "values": data["pid_i"], "color": COLORS["green"]},
            {"label": "D-Anteil", "values": data["pid_d"], "color": COLORS["red"]},
        ],
        filename="pid_terms.svg",
    )


def main() -> None:
    data = read_rows(DEFAULT_CSV)
    make_plots(data)
    print(f"Plots written to {', '.join(str(path) for path in PLOT_DIRS)}")


if __name__ == "__main__":
    main()
