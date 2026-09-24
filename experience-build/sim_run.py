import json
import logging
import math
import os
import shutil
from datetime import datetime

from signalflag.sdk.metrics import Emitter

# Ensure the outputs directory exists
os.makedirs("/tmp/resim/outputs/", exist_ok=True)

# Set up logging
logging.basicConfig(
    filename="/tmp/resim/outputs/processed_flight_log.json",
    level=logging.INFO,
    format="%(message)s",  # We'll just log the raw JSON data
    datefmt="%Y-%m-%d %H:%M:%S",
)


HEALTH_EVENTS = {
    "WARNING": ("Health warning", "FAIL_WARN"),
    "ERROR": ("Health error", "FAIL_BLOCK"),
    "OK": ("Health back to OK", "PASSED"),
}

# The same palette as the Flight Path chart in .resim/metrics/templates/.
HEALTH_COLORS = {"OK": "#4e79a7", "WARNING": "#f28e2b", "ERROR": "#e15759"}
LIMIT_COLOR = "#e15759"
PATH_COLOR = "rgba(128, 128, 128, 0.5)"

# Samples of context to show either side of a health excursion.
EXCURSION_CONTEXT = 10


class Flight:
    """A flight log as parallel lists, one entry per sample."""

    def __init__(self, flight_data):
        samples = flight_data["samples"]
        start = datetime.fromisoformat(samples[0]["timestamp"])
        self.times = [(datetime.fromisoformat(s["timestamp"]) - start).total_seconds() for s in samples]
        self.xs = [float(s["position"]["x"]) for s in samples]
        self.ys = [float(s["position"]["y"]) for s in samples]
        self.zs = [float(s["position"]["z"]) for s in samples]
        self.speeds = [float(s["speed"]) for s in samples]
        self.states = [s["state"] for s in samples]
        self.flags = [s["status"] for s in samples]
        self.health = [flag.upper() for flag in self.flags]
        limits = flight_data.get("metadata", {}).get("limits", {})
        self.ceiling = limits.get("altitude_ceiling_m")
        self.geofence = limits.get("geofence_radius_m")

    def __len__(self):
        return len(self.times)

    def distance(self, i):
        return math.hypot(self.xs[i], self.ys[i])

    def describe(self, i):
        return f"{self.zs[i]:.1f} m altitude, {self.distance(i):.0f} m from the launch pad"

    def excursions(self):
        """Each run of samples whose health flag is not OK, as (first, last) indices."""
        runs, start = [], None
        for i, health in enumerate(self.health):
            if health != "OK" and start is None:
                start = i
            elif health == "OK" and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            runs.append((start, len(self) - 1))
        return runs

    def duration(self, first, last):
        """Seconds from the first sample to the one after the last, or to the last if it ends the flight."""
        end = self.times[last + 1] if last + 1 < len(self) else self.times[last]
        return end - self.times[first]


TABLE_ROW_HEIGHT = 28


def table_metric(name, rows, description="", status="PASSED"):
    """One plotly table of (label, value) rows, so an event's numbers read as a single panel."""
    return {
        "name": name,
        "type": "plotly",
        "description": description,
        "status": status,
        "value": {
            "data": [{
                "type": "table",
                "columnwidth": [3, 2],
                "header": {
                    "values": ["Metric", "Value"],
                    "align": ["left", "right"],
                    "fill": {"color": HEALTH_COLORS["OK"]},
                    "font": {"color": "white", "size": 13},
                    "height": TABLE_ROW_HEIGHT,
                },
                "cells": {
                    "values": [[label for label, _ in rows], [value for _, value in rows]],
                    "align": ["left", "right"],
                    "fill": {"color": [["#f2f2f2" if k % 2 == 0 else "#ffffff" for k in range(len(rows))]]},
                    "font": {"color": "#222222", "size": 13},
                    "height": TABLE_ROW_HEIGHT,
                },
            }],
            "layout": {
                "height": TABLE_ROW_HEIGHT * (len(rows) + 1) + 20,
                "margin": {"l": 10, "r": 10, "t": 10, "b": 10},
                "plot_bgcolor": "rgba(0, 0, 0, 0)",
                "paper_bgcolor": "rgba(0, 0, 0, 0)",
            },
        },
    }


def fixed(value, places):
    """Format to a fixed number of decimal places, never showing -0.0."""
    return f"{round(value, places) + 0.0:.{places}f}"


def position_rows(flight, i):
    return [
        ("Flight time (s)", fixed(flight.times[i], 0)),
        ("Speed (m/s)", fixed(flight.speeds[i], 1)),
        ("Altitude (m)", fixed(flight.zs[i], 1)),
        ("East of launch pad (m)", fixed(flight.xs[i], 1)),
        ("North of launch pad (m)", fixed(flight.ys[i], 1)),
        ("Distance from launch pad (m)", fixed(flight.distance(i), 0)),
    ]


def flight_totals(flight):
    flown = sum(
        math.dist((flight.xs[i], flight.ys[i], flight.zs[i]), (flight.xs[i + 1], flight.ys[i + 1], flight.zs[i + 1]))
        for i in range(len(flight) - 1)
    )
    return table_metric("Flight totals", [
        ("Flight duration (s)", fixed(flight.times[-1], 0)),
        ("Distance flown (m)", fixed(flown, 0)),
        ("Maximum altitude (m)", fixed(max(flight.zs), 1)),
        ("Maximum speed (m/s)", fixed(max(flight.speeds), 1)),
    ])


def chart_layout(x_title, y_title, equal_axes=False):
    layout = {
        "xaxis": {"title": {"text": x_title}, "zeroline": False},
        "yaxis": {"title": {"text": y_title}, "zeroline": False},
        "plot_bgcolor": "rgba(0, 0, 0, 0)",
        "paper_bgcolor": "rgba(0, 0, 0, 0)",
        "showlegend": True,
        "hovermode": "closest",
    }
    if equal_axes:
        layout["yaxis"].update({"scaleanchor": "x", "scaleratio": 1})
    return layout


# Padding around a zoomed map view: a fraction of its size, plus a fixed margin.
ZOOM_PADDING = 0.15
ZOOM_MARGIN_M = 10.0


def zoom_box(flight, first, last):
    """A square (x0, x1, y0, y1) around an excursion and the samples either side of it.

    Including the last sample before and the first after shows the path crossing the
    boundary, not only the stretch beyond it.
    """
    lo, hi = max(0, first - 1), min(len(flight) - 1, last + 1)
    xs, ys = flight.xs[lo:hi + 1], flight.ys[lo:hi + 1]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 * (1 + ZOOM_PADDING) + ZOOM_MARGIN_M
    return cx - half, cx + half, cy - half, cy + half


def geofence_arc(radius, box):
    """Points on the geofence circle that fall inside box, with None where the arc leaves it."""
    x0, x1, y0, y1 = box
    # A little slack so the arc runs to the edge of the view before it is clipped.
    slack = (x1 - x0) * 0.05
    xs, ys, inside_before = [], [], False
    steps = 1440
    for k in range(steps + 1):
        angle = 2 * math.pi * k / steps
        x, y = radius * math.cos(angle), radius * math.sin(angle)
        inside = x0 - slack <= x <= x1 + slack and y0 - slack <= y <= y1 + slack
        if inside:
            xs.append(x)
            ys.append(y)
        elif inside_before:
            xs.append(None)
            ys.append(None)
        inside_before = inside
    return xs, ys


def path_chart(flight, first, last, status, zoom=True):
    """The flight from above, with the excursion highlighted and the geofence drawn.

    With zoom, the view covers only the excursion and a small buffer around it, and
    only the part of the geofence inside that view is drawn.
    """
    colors = [HEALTH_COLORS["OK"]] * len(flight)
    for i in range(first, last + 1):
        colors[i] = HEALTH_COLORS.get(flight.health[i], HEALTH_COLORS["OK"])
    box = zoom_box(flight, first, last) if zoom else None
    data = [{
        "x": flight.xs,
        "y": flight.ys,
        "type": "scatter",
        "mode": "lines+markers",
        "name": "Flight path",
        "line": {"color": PATH_COLOR, "width": 2},
        "marker": {"size": 6, "color": colors},
    }]
    if flight.geofence:
        if box:
            arc_x, arc_y = geofence_arc(flight.geofence, box)
        else:
            steps = 96
            arc_x = [flight.geofence * math.cos(2 * math.pi * k / steps) for k in range(steps + 1)]
            arc_y = [flight.geofence * math.sin(2 * math.pi * k / steps) for k in range(steps + 1)]
        data.append({
            "x": arc_x,
            "y": arc_y,
            "type": "scatter",
            "mode": "lines",
            "name": f"Geofence ({flight.geofence:.0f} m)",
            "line": {"color": LIMIT_COLOR, "dash": "dash"},
        })
    if not box or (box[0] <= 0 <= box[1] and box[2] <= 0 <= box[3]):
        data.append({
            "x": [0],
            "y": [0],
            "type": "scatter",
            "mode": "markers",
            "name": "Launch pad",
            "marker": {"symbol": "star", "size": 14, "color": "#59a14f"},
        })
    layout = chart_layout("East (m)", "North (m)", equal_axes=True)
    if box:
        # constrain: domain keeps these exact ranges at equal scale by shrinking the
        # plot area, where the default would widen one axis instead.
        layout["xaxis"].update({"range": [box[0], box[1]], "constrain": "domain"})
        layout["yaxis"].update({"range": [box[2], box[3]], "constrain": "domain"})
        description = "The part of the route that left the geofence, seen from above. Highlighted samples are the ones outside it."
    else:
        description = "The route flown, seen from above. Highlighted samples are the ones with a health flag."
    return {
        "name": "Flight path and geofence",
        "type": "plotly",
        "description": description,
        "status": status,
        "value": {"data": data, "layout": layout},
    }


def altitude_chart(flight, first, last, status):
    """Altitude around the excursion, with the ceiling drawn."""
    lo = max(0, first - EXCURSION_CONTEXT)
    hi = min(len(flight) - 1, last + EXCURSION_CONTEXT)
    window = range(lo, hi + 1)
    data = [{
        "x": [flight.times[i] for i in window],
        "y": [flight.zs[i] for i in window],
        "type": "scatter",
        "mode": "lines+markers",
        "name": "Altitude",
        "line": {"color": PATH_COLOR, "width": 2},
        "marker": {
            "size": 6,
            "color": [
                HEALTH_COLORS.get(flight.health[i], HEALTH_COLORS["OK"]) if first <= i <= last else HEALTH_COLORS["OK"]
                for i in window
            ],
        },
    }]
    if flight.ceiling:
        data.append({
            "x": [flight.times[lo], flight.times[hi]],
            "y": [flight.ceiling, flight.ceiling],
            "type": "scatter",
            "mode": "lines",
            "name": f"Altitude ceiling ({flight.ceiling:.0f} m)",
            "line": {"color": LIMIT_COLOR, "dash": "dash"},
        })
    return {
        "name": "Altitude above the ceiling",
        "type": "plotly",
        "description": f"Altitude from {EXCURSION_CONTEXT} s before to {EXCURSION_CONTEXT} s after the excursion.",
        "status": status,
        "value": {"data": data, "layout": chart_layout("Flight time (s)", "Altitude (m)")},
    }


def excursion_metrics(flight, first, last, status):
    """A chart for each limit the flight broke during an excursion, and a table summarizing it."""
    run = range(first, last + 1)
    duration = fixed(flight.duration(first, last), 0)
    broke_fence = flight.geofence and max(flight.distance(i) for i in run) > flight.geofence
    broke_ceiling = flight.ceiling and max(flight.zs[i] for i in run) > flight.ceiling
    charts, rows = [], [("Flight time at start (s)", fixed(flight.times[first], 0))]
    if broke_fence:
        charts.append(path_chart(flight, first, last, status))
        rows += [
            ("Geofence radius (m)", fixed(flight.geofence, 0)),
            ("Maximum distance from launch pad (m)", fixed(max(flight.distance(i) for i in run), 0)),
            ("Time outside geofence (s)", duration),
        ]
    if broke_ceiling:
        charts.append(altitude_chart(flight, first, last, status))
        rows += [
            ("Altitude ceiling (m)", fixed(flight.ceiling, 0)),
            ("Peak altitude (m)", fixed(max(flight.zs[i] for i in run), 1)),
            ("Time above ceiling (s)", duration),
        ]
    if not charts:
        # No known limit explains the flag, so show where and how high the flight was.
        charts = [path_chart(flight, first, last, status, zoom=False), altitude_chart(flight, first, last, status)]
        rows.append(("Duration (s)", duration))
    return charts + [table_metric("Excursion summary", rows, status=status)]


def emit_flight_samples(flight_data):
    """Emit the data for the metrics in .resim/metrics/config.resim.yml.

    Every sample becomes a flight_sample row. Changes of flight state and of the
    drone's health flag also become flight_event events, which appear on the test's
    Events tab with metrics of their own. A health warning or error event carries a
    FAIL_WARN or FAIL_BLOCK status, so it counts toward the test's result, and charts
    the limit the flight broke.

    Timestamps are nanoseconds since the first sample, so every flight starts at zero
    on a time axis.
    """
    flight = Flight(flight_data)
    excursion_starting = {first: (first, last) for first, last in flight.excursions()}
    excursion_ending = {last + 1: (first, last) for first, last in flight.excursions()}
    with Emitter() as emitter:
        for i in range(len(flight)):
            timestamp = int(flight.times[i] * 1e9)
            emitter.emit(
                "flight_sample",
                {
                    "speed": flight.speeds[i],
                    "state": flight.states[i],
                    "flight_status": flight.flags[i],
                    "x": flight.xs[i],
                    "y": flight.ys[i],
                    "z": flight.zs[i],
                },
                timestamp=timestamp,
            )
            if i == 0:
                continue

            if flight.states[i] != flight.states[i - 1]:
                # A return to Idle after takeoff means the drone is back on the ground.
                landed = flight.states[i] == "Idle"
                emitter.emit_event(
                    "flight_event",
                    {
                        "name": "Landed" if landed else flight.states[i],
                        "description": f"{flight.states[i - 1]} to {flight.states[i]} at {flight.describe(i)}.",
                        "status": "PASSED",
                        "tags": ["flight-state"],
                        "metrics": [flight_totals(flight) if landed else table_metric("Position and speed", position_rows(flight, i))],
                    },
                    timestamp=timestamp,
                )

            health = flight.health[i]
            if health != flight.health[i - 1] and health in HEALTH_EVENTS:
                name, status = HEALTH_EVENTS[health]
                if i in excursion_starting:
                    metrics = excursion_metrics(flight, *excursion_starting[i], status)
                else:
                    rows = position_rows(flight, i)
                    if i in excursion_ending:
                        first, last = excursion_ending[i]
                        rows.append(("Excursion duration (s)", fixed(flight.duration(first, last), 0)))
                    metrics = [table_metric("Position and speed", rows)]
                emitter.emit_event(
                    "flight_event",
                    {
                        "name": name,
                        "description": f"The drone reported {flight.flags[i]} at {flight.describe(i)}.",
                        "status": status,
                        "tags": ["health"],
                        "metrics": metrics,
                    },
                    timestamp=timestamp,
                )


def main():
    print("Starting simulation run...")

    # Read the test_config.json file to get the experience location
    config_path = "/tmp/resim/test_config.json"
    try:
        with open(config_path, "r") as f:
            test_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find config file at {config_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        return

    experience_location = test_config["experienceLocation"]
    print(f"Experience location: {experience_location}")

    # Read the flight_log.json directly from the experience location
    src_flight_log = os.path.join(experience_location, "flight_log.json")
    try:
        with open(src_flight_log, "r") as f:
            flight_data = json.load(f)
        print(f"Successfully loaded flight data from {src_flight_log}")
    except FileNotFoundError:
        print(f"Error: Could not find flight log at {src_flight_log}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in flight log: {e}")
        return

    # Write the flight data to the output log
    with open("/tmp/resim/outputs/processed_flight_log.json", "w") as f:
        json.dump(flight_data, f, indent=2)

    emit_flight_samples(flight_data)

    print("Completed writing flight data. Exiting.")


if __name__ == "__main__":
    main()
