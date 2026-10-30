import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import imageio

from resim.metrics.python.emissions import Emitter

logger = logging.getLogger(__name__)

# The transfer-cube reward is a stage ladder rather than a score, so each value
# names a point in the task. See custom_transfer_cube.CustomTransferCubeTask.
STAGES = {
    0: "no contact",
    1: "right gripper contact",
    2: "lifted",
    3: "transfer attempted",
    4: "handover complete",
}

# The event raised the first time an episode reaches each stage. Stage 0 is the
# starting state, so it is not an event.
STAGE_EVENTS = {
    1: ("Cube Contacted", "The right gripper made contact with the cube."),
    2: ("Cube Lifted", "The right gripper lifted the cube clear of the table."),
    3: ("Transfer Attempted", "The left gripper made contact with the cube."),
    4: ("Handover Complete", "The cube crossed the handover line in the left gripper."),
}

# World x the cube must cross for the handover to count, per the environment's
# reward function. The cube spawns between 0.0 and 0.2, so it travels negative.
HANDOVER_X_M = -0.10

CONFIG_PATH = Path(__file__).resolve().parents[2] / ".resim/metrics/config.resim.yml"

# One blue ordinal ramp per surface, a step per stage. Stage is a rung on a
# ladder rather than an unordered label, so lightness carries magnitude. Each
# set is chosen for its own surface rather than flipped from the other: the
# step nearest the surface has to stay visible against it, and no single
# five-step ramp clears that on both.
#
# On light the ramp runs light to dark, so later stages darken. On dark it runs
# the other way, so later stages brighten and the earliest recedes.
STAGE_COLORS = {
    "light": {
        0: "#86b6ef",
        1: "#5598e7",
        2: "#2a78d6",
        3: "#1c5cab",
        4: "#104281",
    },
    "dark": {
        0: "#184f95",
        1: "#2a78d6",
        2: "#6da7ec",
        3: "#9ec5f4",
        4: "#cde2fb",
    },
}
# Axis, label and reference-line ink. Text never wears a series colour.
INK = {
    "light": {"muted": "#898781", "secondary": "#52514e",
              "grid": "#e1e0d9", "surface": "#fcfcfb"},
    "dark": {"muted": "#898781", "secondary": "#c3c2b7",
             "grid": "#2c2c2a", "surface": "#1a1a19"},
}
TRAJECTORY_MODE = "dark"

GIF_NAME = "episode.gif"
# Frames are subsampled to this rate and played back at it, so the replay runs
# at the same speed as the episode however long the episode was.
GIF_FPS = 10.0


def make_emitter(config_path: Optional[Path] = None) -> Emitter:
    """Open an emitter writing to the job's output directory.

    Emissions are validated against the metrics config, so a topic that drifts
    away from the config fails here rather than rendering as an empty chart.
    """
    path = CONFIG_PATH if config_path is None else config_path
    if not path.is_file():
        logger.warning("No metrics config at %s, emitting without validation", path)
    return Emitter(config_path=path)


def _count_regressions(rewards: Sequence[Any], upto: int) -> int:
    """Times the episode fell back to an earlier stage in steps 0 to ``upto``.

    A policy that reaches a stage after dropping the cube twice is worse than
    one that goes straight there, which the stage alone does not distinguish.
    """
    return sum(
        1
        for index in range(1, min(upto, len(rewards) - 1) + 1)
        if int(rewards[index]) < int(rewards[index - 1])
    )


def _write_episode_gif(
    frames: List[Any], times: Sequence[float], output_dir: Path
) -> Optional[str]:
    """Write the whole episode as a looping GIF, returning its file name.

    The name is relative to the output directory, which is what the topic
    refers to.
    """
    if not frames:
        return None

    elapsed = times[-1] - times[0] if len(times) > 1 else 0.0
    step_rate = len(frames) / elapsed if elapsed > 0 else GIF_FPS
    stride = max(1, round(step_rate / GIF_FPS))
    # Half resolution on both axes, which is what keeps a whole episode to a
    # sensible size.
    clip = [frame[::2, ::2] for frame in frames[::stride]]

    imageio.mimsave(
        output_dir / GIF_NAME, clip, duration=1.0 / GIF_FPS, loop=0
    )
    return GIF_NAME


def _scalar(name: str, description: str, value: float, places: int) -> Dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "type": "scalar",
        "value": str(round(value, places)),
        "status": "PASSED",
    }


def _trajectory_figure(
    cube_positions: List[Any], rewards: Sequence[Any], mode: str = TRAJECTORY_MODE
) -> str:
    """A top-down view of the cube's path, as Plotly JSON.

    The per-axis charts each project this motion onto one axis against time,
    which cannot show the shape of the path. One series per stage so identity
    is carried by a legend rather than by color alone.
    """
    import plotly.graph_objects as go

    colors = STAGE_COLORS[mode]
    ink = INK[mode]

    xs = [float(p[0]) for p in cube_positions]
    ys = [float(p[1]) for p in cube_positions]
    stages = [int(r) for r in rewards]

    figure = go.Figure()
    # Colour the path itself rather than scattering a marker per step: at 600
    # steps markers overlap into an unreadable band, while segments keep the
    # shape of the path legible and still carry stage by colour.
    labelled: set[int] = set()
    start = 0
    for index in range(1, len(stages) + 1):
        if index < len(stages) and stages[index] == stages[start]:
            continue
        stage = stages[start]
        # Extend one point into the next run so segments join without gaps.
        end = min(index + 1, len(stages))
        figure.add_trace(
            go.Scatter(
                x=xs[start:end],
                y=ys[start:end],
                mode="lines",
                line={"color": colors.get(stage, ink["muted"]), "width": 2},
                name=STAGES.get(stage, "unknown"),
                legendgroup=str(stage),
                showlegend=stage not in labelled,
                hovertemplate="x=%{x:.3f} m<br>y=%{y:.3f} m<extra>%{fullData.name}</extra>",
            )
        )
        labelled.add(stage)
        start = index

    # Markers only where something happens: the start, and the first time each
    # stage is reached. Selective labels rather than a number on every point.
    marks_x, marks_y, marks_text, marks_color = [xs[0]], [ys[0]], ["start"], [ink["muted"]]
    seen: set[int] = set()
    for x, y, stage in zip(xs, ys, stages):
        if stage in seen or stage == 0:
            continue
        seen.add(stage)
        marks_x.append(x)
        marks_y.append(y)
        marks_text.append(STAGES.get(stage, "unknown"))
        marks_color.append(colors.get(stage, ink["muted"]))
    figure.add_trace(
        go.Scatter(
            x=marks_x,
            y=marks_y,
            mode="markers",
            marker={
                "size": 11,
                "color": marks_color,
                "line": {"color": ink["surface"], "width": 2},
            },
            text=marks_text,
            name="first reached",
            showlegend=False,
            hovertemplate="%{text}<br>x=%{x:.3f} m<br>y=%{y:.3f} m<extra></extra>",
        )
    )
    # Reference line, not a series: neutral ink and dashed.
    figure.add_vline(
        x=HANDOVER_X_M,
        line={"color": ink["muted"], "width": 2, "dash": "dash"},
        annotation={"text": "handover line", "font": {"color": ink["secondary"]}},
        annotation_position="top",
    )
    figure.update_layout(
        title="Cube path, viewed from above",
        xaxis={
            "title": "x (m), toward the left arm",
            "gridcolor": ink["grid"],
            "zeroline": False,
        },
        # Equal aspect: this is a spatial plot, so distances must not distort.
        yaxis={
            "title": "y (m)",
            "gridcolor": ink["grid"],
            "zeroline": False,
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        font={"color": ink["secondary"]},
        paper_bgcolor=ink["surface"],
        plot_bgcolor=ink["surface"],
        hovermode="closest",
        legend={"title": {"text": "Stage"}},
    )
    return str(figure.to_json())


def emit_episode(emitter: Emitter, results: Dict[str, Any], output_dir: Path) -> None:
    """Emit one episode's per-step signals, its stage events, and its summary.

    Values are cast to Python types on the way out: the rewards arrive as a
    numpy array, and numpy scalars do not satisfy the config's float fields.
    """
    times = results["times"]
    rewards = results["rewards"]
    cube_positions = results["cube_positions"]
    frames = results["frames"]
    timestamps = [int(time * 1e9) for time in times]

    emitter.emit_series(
        "step_reward",
        {"reward": [float(reward) for reward in rewards]},
        timestamps,
    )
    emitter.emit_series(
        "task_stage",
        {"state": [STAGES.get(int(reward), "unknown") for reward in rewards]},
        timestamps,
    )
    emitter.emit_series(
        "cube_pose",
        {
            "x": [float(position[0]) for position in cube_positions],
            "y": [float(position[1]) for position in cube_positions],
            "z": [float(position[2]) for position in cube_positions],
        },
        timestamps,
    )

    # The same timings go out twice: on the event, where they explain one
    # transition, and as a topic, where they chart and aggregate across seeds.
    timing: Dict[str, List[Any]] = {
        "stage": [],
        "seconds_from_start": [],
        "seconds_from_previous": [],
        "regressions": [],
    }
    timing_timestamps: List[int] = []

    # Keyed on stages already seen rather than a running maximum: the reward
    # can skip a rung, then visit it later, and that visit still happened.
    seen: set[int] = set()
    previous_index = 0
    for index, reward in enumerate(rewards):
        stage = int(reward)
        if stage in seen or stage not in STAGE_EVENTS:
            continue
        seen.add(stage)
        name, description = STAGE_EVENTS[stage]
        stage_name = STAGES[stage]

        seconds_from_start = float(times[index] - times[0])
        seconds_from_previous = float(times[index] - times[previous_index])
        regressions = _count_regressions(rewards, index)
        margin = HANDOVER_X_M - float(cube_positions[index][0])

        timing["stage"].append(stage_name)
        timing["seconds_from_start"].append(seconds_from_start)
        timing["seconds_from_previous"].append(seconds_from_previous)
        timing["regressions"].append(regressions)
        timing_timestamps.append(timestamps[index])

        metrics: List[Dict[str, Any]] = [
            _scalar(
                "Time to Stage (s)",
                "Simulated seconds from the start of the episode.",
                seconds_from_start,
                2,
            ),
            _scalar(
                "Time in Previous Stage (s)",
                "Simulated seconds since the episode reached the stage before.",
                seconds_from_previous,
                2,
            ),
            _scalar(
                "Ladder Regressions",
                "Times the episode fell back to an earlier stage before this one.",
                regressions,
                0,
            ),
            _scalar(
                "Handover Margin (m)",
                f"Distance past the handover line at x = {HANDOVER_X_M} m. "
                "Positive once the cube has crossed it.",
                margin,
                3,
            ),
        ]

        emitter.emit_event(
            "stage_reached",
            {
                "name": name,
                "description": description,
                "status": "PASSED",
                "tags": ["manipulation", stage_name],
                "metrics": metrics,
            },
            timestamps[index],
        )
        previous_index = index

    if timing_timestamps:
        emitter.emit_series("stage_timing", timing, timing_timestamps)

    gif = _write_episode_gif(frames, times, output_dir)
    if gif is not None:
        emitter.emit("episode_gif", {"filename": gif})

    emitter.emit(
        "cube_trajectory",
        {"raw_metric": _trajectory_figure(cube_positions, rewards)},
    )

    # Counted over the whole episode. The per-stage count only covers what
    # happened before that stage, so a policy that peaks early and then
    # oscillates records nothing there.
    total_regressions = _count_regressions(rewards, len(rewards) - 1)

    episode_seconds = times[-1] - times[0]
    emitter.emit(
        "summary_metrics",
        {
            "overall_success_rate": 100.0 if results["is_success"] else 0.0,
            "overall_average_sum_reward": float(rewards.sum()),
            "overall_average_max_reward": float(rewards.max()),
            "total_evaluation_time": float(episode_seconds),
            "total_regressions": total_regressions,
        },
    )
    logger.info(
        "Emitted %d steps, furthest stage %r, %d regressions",
        len(timestamps),
        STAGES[int(rewards.max())],
        total_regressions,
    )
