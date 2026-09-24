"""Generate the demo's flight logs in experience-build/experiences/.

Each flight is simulated at 10 Hz as a drone flying a list of legs, with speed and
acceleration limits so it rounds corners the way a real multirotor does, then recorded
at 1 Hz with GPS-like position noise. Positions are meters east (x), north (y), and up
(z) from the launch pad.

The health flag in each sample comes from a rule the flight actually trips:

- Drone Flight with Warning climbs above the 120 m altitude ceiling on part of its
  route, and reports WARNING while it is above it.
- Drone Flight with Error overshoots the 350 m geofence around the launch pad, and
  reports Error while it is outside.

Run from the repository root:

    python3 tools/generate_flight_logs.py
"""

import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

EXPERIENCES = Path(__file__).resolve().parent.parent / "experience-build" / "experiences"

SIM_HZ = 10
RECORD_EVERY = SIM_HZ  # one recorded sample per second
MAX_ACCEL = 3.0  # m/s^2
GPS_NOISE_XY = 0.4  # m, one standard deviation
GPS_NOISE_Z = 0.3
SPEED_NOISE = 0.1  # m/s

ALTITUDE_CEILING = 120.0  # m
GEOFENCE_RADIUS = 350.0  # m; the survey lap stays within about 300 m of the pad

# A survey lap around the launch pad, as (x, y) waypoints in meters.
SURVEY_LAP = [(120, 40), (220, 160), (140, 260), (-20, 220), (-80, 90)]

UNITS = {
    "speed": "m/s",
    "position": {"x": "m", "y": "m", "z": "m"},
    "time": "s",
}


def lap_legs(altitude, speed, hover_at=None, hover_s=0.0, altitude_by_waypoint=None, extra=None):
    """Takeoff, fly the survey lap, return home, hover, and land."""
    waypoints = list(SURVEY_LAP)
    if extra:
        index, point = extra
        waypoints.insert(index, point)
    legs = [{"to": (0.0, 0.0, altitude), "speed": 3.0, "state": "Takeoff", "tol": 0.5}]
    for i, (x, y) in enumerate(waypoints):
        z = (altitude_by_waypoint or {}).get(i, altitude)
        legs.append({
            "to": (float(x), float(y), z),
            "speed": speed,
            "state": "Moving",
            "tol": max(3.0, speed),
            "hold": hover_s if i == hover_at else 0.0,
        })
    legs.append({"to": (0.0, 0.0, altitude), "speed": speed, "state": "Moving", "tol": 1.0, "hold": 3.0})
    legs.append({"to": (0.0, 0.0, 0.0), "speed": 2.0, "state": "Landing", "tol": 0.2})
    return legs


FLIGHTS = {
    "maiden_drone_flight": {
        "start": datetime(2024, 3, 18, 10, 0, 0),
        "seed": 1,
        "legs": lap_legs(altitude=40.0, speed=6.0, hover_at=2, hover_s=5.0),
        "status": lambda x, y, z: "OK",
    },
    "fast_drone_flight": {
        "start": datetime(2024, 3, 18, 11, 0, 0),
        "seed": 2,
        "legs": lap_legs(altitude=40.0, speed=15.0),
        "status": lambda x, y, z: "OK",
    },
    "warning_drone_flight": {
        "start": datetime(2024, 3, 18, 12, 0, 0),
        "seed": 3,
        # Climbs to 145 m over the far side of the lap.
        "legs": lap_legs(altitude=60.0, speed=10.0, altitude_by_waypoint={1: 145.0, 2: 145.0}),
        "status": lambda x, y, z: "WARNING" if z > ALTITUDE_CEILING else "OK",
    },
    "error_drone_flight": {
        "start": datetime(2024, 3, 18, 13, 0, 0),
        "seed": 4,
        # Overshoots east of the lap, well past the geofence, before turning back.
        "legs": lap_legs(altitude=60.0, speed=12.0, extra=(2, (390, 200))),
        "status": lambda x, y, z: "Error" if math.hypot(x, y) > GEOFENCE_RADIUS else "OK",
    },
}


def simulate(legs, idle_s=3.0):
    """Yield (position, velocity, state) at SIM_HZ for the whole flight."""
    dt = 1.0 / SIM_HZ
    pos = [0.0, 0.0, 0.0]
    vel = [0.0, 0.0, 0.0]

    for _ in range(int(idle_s * SIM_HZ)):
        yield tuple(pos), (0.0, 0.0, 0.0), "Idle"

    for leg in legs:
        target, speed, tol = leg["to"], leg["speed"], leg["tol"]
        while True:
            delta = [t - p for t, p in zip(target, pos)]
            dist = math.sqrt(sum(d * d for d in delta))
            if dist <= tol:
                break
            # Slow down on the final approach so the drone does not overshoot its stop.
            approach = min(speed, math.sqrt(2 * MAX_ACCEL * dist)) if leg.get("hold") or leg["state"] != "Moving" else speed
            desired = [d / dist * approach for d in delta]
            change = [dv - v for dv, v in zip(desired, vel)]
            mag = math.sqrt(sum(c * c for c in change))
            limit = MAX_ACCEL * dt
            if mag > limit:
                change = [c / mag * limit for c in change]
            vel = [v + c for v, c in zip(vel, change)]
            pos = [p + v * dt for p, v in zip(pos, vel)]
            pos[2] = max(pos[2], 0.0)
            yield tuple(pos), tuple(vel), leg["state"]

        hold = leg.get("hold", 0.0)
        if hold:
            vel = [0.0, 0.0, 0.0]
            for _ in range(int(hold * SIM_HZ)):
                yield tuple(pos), (0.0, 0.0, 0.0), "Hovering"

    vel = [0.0, 0.0, 0.0]
    pos[2] = 0.0
    for _ in range(int(idle_s * SIM_HZ)):
        yield tuple(pos), (0.0, 0.0, 0.0), "Idle"


def record(flight):
    rng = random.Random(flight["seed"])
    samples = []
    for i, (pos, vel, state) in enumerate(simulate(flight["legs"])):
        if i % RECORD_EVERY:
            continue
        on_ground = state == "Idle"
        x = pos[0] + (0.0 if on_ground else rng.gauss(0, GPS_NOISE_XY))
        y = pos[1] + (0.0 if on_ground else rng.gauss(0, GPS_NOISE_XY))
        z = max(0.0, pos[2] + (0.0 if on_ground else rng.gauss(0, GPS_NOISE_Z)))
        speed = math.sqrt(sum(v * v for v in vel))
        if not on_ground:
            speed = max(0.0, speed + rng.gauss(0, SPEED_NOISE))
        samples.append({
            "timestamp": (flight["start"] + timedelta(seconds=len(samples))).isoformat(),
            "speed": round(speed, 2),
            "state": state,
            "status": flight["status"](pos[0], pos[1], pos[2]),
            # Adding 0.0 turns a rounded -0.0 into 0.0.
            "position": {"x": round(x, 2) + 0.0, "y": round(y, 2) + 0.0, "z": round(z, 2) + 0.0},
        })
    return samples


def main():
    for name, flight in FLIGHTS.items():
        samples = record(flight)
        out = EXPERIENCES / name / "flight_log.json"
        metadata = {
            "units": UNITS,
            # The operating limits the drone checks itself against. The simulator
            # draws them on the charts it attaches to health events.
            "limits": {
                "altitude_ceiling_m": ALTITUDE_CEILING,
                "geofence_radius_m": GEOFENCE_RADIUS,
            },
        }
        out.write_text(json.dumps({"metadata": metadata, "samples": samples}, indent=2) + "\n")
        print(f"{name}: {len(samples)} samples -> {out.relative_to(EXPERIENCES.parent.parent)}")


if __name__ == "__main__":
    main()
