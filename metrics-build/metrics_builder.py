import json
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import plotly.graph_objects as go  # type: ignore
from resim.metrics.fetch_job_metrics import (fetch_job_metrics,
                                             fetch_job_metrics_by_batch)
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
from resim.metrics.python.metrics import (  # type: ignore[attr-defined, import]
    DoubleFailureDefinition, DoubleOverTimeMetric, HistogramBucket,
    MetricImportance, MetricStatus, PlotlyMetric, ScalarMetric,
    SeriesMetricsData, StatesOverTimeMetric, TextMetric, Timestamp)
from resim.metrics.python.metrics_writer import ResimMetricsWriter

BATCH_METRICS_CONFIG_PATH = Path("/tmp/resim/inputs/batch_metrics_config.json")


def read_flight_data(filename: str) -> dict:
    """Read and parse flight data from a JSON file.

    Args:
        filename: Path to the flight log JSON file

    Returns:
        dict: Parsed flight data containing metadata and samples
    """
    input_path = Path("/tmp/resim/inputs/logs") / filename
    if not input_path.exists():
        raise FileNotFoundError(f"Flight log file not found at {input_path}")

    with open(input_path, "r") as f:
        data = json.load(f)

    # Validate the expected structure
    if not isinstance(data, dict):
        raise ValueError("Flight log must be a JSON object")
    if "metadata" not in data:
        raise ValueError("Flight log must contain metadata")
    if "samples" not in data:
        raise ValueError("Flight log must contain samples")

    return data


def add_scalar_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    """Add scalar metrics including maximum speed achieved during flight."""
    # Maximum speed metric
    max_speed = max(sample["speed"] for sample in flight_data["samples"])
    (
        metrics_writer.add_scalar_metric("Maximum Speed")
        .with_description("Maximum speed achieved during flight")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_value(max_speed)
        .with_unit("m/s")
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
    )


def add_speed_over_time_plot(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Add time series metrics for speed measurements over time."""
    # Extract speed data over time
    timestamps = []
    speeds = []
    statuses = []
    has_error = False
    has_warning = False

    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
        timestamps.append(dt)
        speeds.append(sample["speed"])

        # Track status from flight data
        if sample["status"] == "Error":
            has_error = True
            statuses.append(
                MetricStatus.FAIL_BLOCK_METRIC_STATUS
            )  # Using FAIL_BLOCK_METRIC_STATUS for errors
        elif sample["status"].lower() == "warning":
            has_warning = True
            statuses.append(
                MetricStatus.FAIL_WARN_METRIC_STATUS
            )  # Using FAIL_WARN_METRIC_STATUS for warnings
        else:
            statuses.append(MetricStatus.PASSED_METRIC_STATUS)

    # Create Plotly figure
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=speeds,
            mode="lines+markers",
            name="Speed",
            line=dict(color="blue"),
            marker=dict(size=6),
        )
    )

    # Update layout
    fig.update_layout(
        title="Speed Over Time",
        xaxis_title="Time",
        yaxis_title="Speed (m/s)",
        showlegend=True,
        template="plotly_white",
    )

    # Determine overall metric status
    overall_status = (
        MetricStatus.FAIL_BLOCK_METRIC_STATUS  # Using FAIL_BLOCK_METRIC_STATUS for errors
        if has_error
        else (
            MetricStatus.FAIL_WARN_METRIC_STATUS  # Using FAIL_WARN_METRIC_STATUS for warnings
            if has_warning
            else MetricStatus.PASSED_METRIC_STATUS
        )
    )

    # Add plotly metric
    (
        metrics_writer.add_plotly_metric("Speed Over Time")
        .with_description("Speed measurements over time with status from flight data")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(overall_status)
        .with_plotly_data(str(fig.to_json()))
    )


def add_altitude_warning_plot(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Add altitude plot with status from flight data."""
    # Extract altitude data over time
    timestamps = []
    altitudes = []
    statuses = []
    has_error = False
    has_warning = False

    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
        timestamps.append(dt)
        altitudes.append(sample["position"]["z"])

        # Track status from flight data
        if sample["status"] == "Error":
            has_error = True
            statuses.append(
                MetricStatus.FAIL_BLOCK_METRIC_STATUS
            )  # Using FAIL_BLOCK_METRIC_STATUS for errors
        elif sample["status"].lower() == "warning":
            has_warning = True
            statuses.append(
                MetricStatus.FAIL_WARN_METRIC_STATUS
            )  # Using FAIL_WARN_METRIC_STATUS for warnings
        else:
            statuses.append(MetricStatus.PASSED_METRIC_STATUS)

    # Create Plotly figure
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=altitudes,
            mode="lines+markers",
            name="Altitude",
            line=dict(color="blue"),
            marker=dict(size=6),
        )
    )

    # Update layout
    fig.update_layout(
        title="Altitude Over Time",
        xaxis_title="Time",
        yaxis_title="Altitude (m)",
        showlegend=True,
        template="plotly_white",
    )

    # Determine overall metric status
    overall_status = (
        MetricStatus.FAIL_BLOCK_METRIC_STATUS  # Using FAIL_BLOCK_METRIC_STATUS for errors
        if has_error
        else (
            MetricStatus.FAIL_WARN_METRIC_STATUS  # Using FAIL_WARN_METRIC_STATUS for warnings
            if has_warning
            else MetricStatus.PASSED_METRIC_STATUS
        )
    )

    # Add plotly metric
    (
        metrics_writer.add_plotly_metric("Altitude Over Time")
        .with_description(
            "Altitude measurements over time with status from flight data"
        )
        .with_importance(MetricImportance.MEDIUM_IMPORTANCE)
        .with_status(overall_status)
        .with_plotly_data(str(fig.to_json()))
    )


def add_states_over_time_plot(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Add time series metrics for flight state transitions."""
    # Extract state data over time
    timestamps = []
    states = []
    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
        timestamps.append(dt)
        states.append(sample["state"])

    # Create a mapping of states to numeric values for coloring
    unique_states = list(set(states))
    state_to_num = {state: i for i, state in enumerate(unique_states)}
    color_values = [state_to_num[state] for state in states]

    # Create Plotly figure
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=color_values,
            mode="markers",
            name="State",
            marker=dict(
                size=10,
                color=color_values,
                colorscale="Viridis",
                colorbar=dict(
                    title="State",
                    ticktext=unique_states,
                    tickvals=list(range(len(unique_states))),
                ),
            ),
        )
    )

    # Update layout
    fig.update_layout(
        title="Flight States Over Time",
        xaxis_title="Time",
        yaxis_title="State",
        showlegend=True,
        template="plotly_white",
        yaxis=dict(
            ticktext=unique_states,
            tickvals=list(range(len(unique_states))),
            range=[-0.5, len(unique_states) - 0.5],
        ),
    )

    # Add plotly metric
    (
        metrics_writer.add_plotly_metric("Flight States Over Time")
        .with_description("Flight state transitions over time")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_plotly_data(str(fig.to_json()))
    )


def add_position_over_time_plot(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Add line plot metrics showing X position over time."""
    # Extract position data and convert timestamps to seconds for x-axis
    x_values = []  # Time in seconds
    y_values = []  # X position values

    start_time = datetime.fromisoformat(
        flight_data["samples"][0]["timestamp"].replace("Z", "+00:00")
    )

    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
        # Convert to seconds from start
        seconds_from_start = (dt - start_time).total_seconds()
        x_values.append(seconds_from_start)
        y_values.append(sample["position"]["x"])

    # Create Plotly figure
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines+markers",
            name="X Position",
            line=dict(color="blue"),
            marker=dict(size=6),
        )
    )

    # Update layout
    fig.update_layout(
        title="X Position Over Time",
        xaxis_title="Time (s)",
        yaxis_title="X Position (m)",
        showlegend=True,
        template="plotly_white",
    )

    # Add plotly metric
    (
        metrics_writer.add_plotly_metric("X Position Over Time")
        .with_description("X-axis position over time")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_plotly_data(str(fig.to_json()))
    )


def add_speed_distribution_plot(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Create and add a histogram showing the distribution of flight speeds."""
    # Extract speed data for histogram
    speeds = [sample["speed"] for sample in flight_data["samples"]]

    # Create Plotly figure
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=speeds,
            name="Speed Distribution",
            nbinsx=10,
            marker_color="blue",
            opacity=0.75,
        )
    )

    # Update layout
    fig.update_layout(
        title="Speed Distribution",
        xaxis_title="Speed (m/s)",
        yaxis_title="Count",
        showlegend=True,
        template="plotly_white",
        bargap=0.1,
    )

    # Add plotly metric
    (
        metrics_writer.add_plotly_metric("Speed Distribution")
        .with_description("Distribution of speeds during flight")
        .with_importance(MetricImportance.MEDIUM_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_plotly_data(str(fig.to_json()))
    )


def add_plotly_metrics_from_flight_data(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    """Create and add a 3D visualization of the flight path using Plotly from raw flight data."""
    # Extract X, Y, Z, and state from flight_data["samples"]
    x = [sample["position"]["x"] for sample in flight_data["samples"]]
    y = [sample["position"]["y"] for sample in flight_data["samples"]]
    z = [sample["position"]["z"] for sample in flight_data["samples"]]
    states = [sample["state"] for sample in flight_data["samples"]]

    # Map states to numeric values for coloring
    unique_states = list(set(states))
    state_to_num = {state: i for i, state in enumerate(unique_states)}
    color_values = [state_to_num[state] for state in states]

    # Create a 3D scatter plot
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=x,
                y=y,
                z=z,
                mode="markers+lines",
                marker=dict(
                    size=6,
                    color=color_values,
                    colorscale="Viridis",
                    opacity=0.8,
                    colorbar=dict(
                        title="State",
                        ticktext=unique_states,
                        tickvals=list(range(len(unique_states))),
                    ),
                ),
            )
        ]
    )

    fig.update_layout(
        title="3D Flight Path",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)"),
    )

    # Add plotly metric
    (
        metrics_writer.add_plotly_metric("3D Flight Path")
        .with_description("Interactive 3D visualization of the flight path")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_plotly_data(str(fig.to_json()))
    )


def add_text_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    total_time = len(flight_data["samples"])
    states = set(sample["state"] for sample in flight_data["samples"])
    max_speed = max(sample["speed"] for sample in flight_data["samples"])

    summary = f"""# Flight Summary
    - Total Duration: {total_time} seconds
    - States Observed: {', '.join(states)}
    - Maximum Speed: {max_speed:.2f} m/s
    - Units: {flight_data['metadata']['units']}
    """

    (
        metrics_writer.add_text_metric("Flight Summary")
        .with_description("Summary of the flight data")
        .with_importance(MetricImportance.MEDIUM_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_text(summary)
    )


def add_altitude_comparison_plot(metrics_writer: ResimMetricsWriter, job_to_metrics: dict) -> None:
    """Create a plot comparing altitude over time across different flights."""
    # Create Plotly figure
    fig = go.Figure()
    
    # Colors for different flights
    colors = ['#636efa', '#EF553B', '#00cc96', '#ab63fa', '#FFA15A', '#19d3f3', '#FF6692', '#B6E880']
    
    for i, (test_id, metrics_proto) in enumerate(job_to_metrics.items()):
        # Find the altitude over time metric
        altitude_data = None
        for metric in metrics_proto.metrics:
            if metric.name == "Altitude Over Time" and isinstance(metric, PlotlyMetric):
                if metric.plotly_data is None:
                    continue
                plotly_data = json.loads(metric.plotly_data)
                if plotly_data and "data" in plotly_data and len(plotly_data["data"]) > 0:
                    altitude_data = plotly_data["data"][0]
                    break
        
        if altitude_data and "x" in altitude_data and "y" in altitude_data:
            # Add trace for this flight
            fig.add_trace(
                go.Scattergl(
                    x=altitude_data["x"],
                    y=altitude_data["y"],
                    mode="lines",
                    name=f"Flight {test_id}",
                    line=dict(
                        color=colors[i % len(colors)],
                        dash="solid"
                    ),
                    marker=dict(symbol="circle"),
                    hovertemplate=f"test=Flight {test_id}<br>time (s)=%{{x}}<br>altitude (m)=%{{y}}<extra></extra>",
                    legendgroup=f"Flight {test_id}",
                    showlegend=True
                )
            )
    
    # Update layout
    fig.update_layout(
        title="Altitude Comparison Across Flights",
        xaxis_title="Time (s)",
        yaxis_title="Altitude (m)",
        showlegend=True,
        template="plotly_white"
    )
    
    # Add plotly metric
    (
        metrics_writer.add_plotly_metric("Altitude Comparison")
        .with_description("Comparison of altitude over time across different flights")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_plotly_data(str(fig.to_json()))
    )


def add_plotly_metrics_from_proto(metrics_writer: ResimMetricsWriter, metrics_proto, job_id=None, job_name=None) -> None:
    """
    Create and add a 3D visualization of the flight path using Plotly,
    extracting X, Y, Z from metrics_proto.metrics_data.
    Optionally, include job_id/job_name in the plot title.
    """
    # Build a lookup for metrics_data by name
    x, y, z = None, None, None
    for data in getattr(metrics_proto, "metrics_data", []):
        if data.name == "X Position Over Time":
            x = getattr(data, "series", None)
        elif data.name == "Y Position Over Time":
            y = getattr(data, "series", None)
        elif data.name == "Altitude Over Time":
            z = getattr(data, "series", None)

    # If any are missing, skip plotting
    if x is None or y is None or z is None:
        print(f"Missing X, Y, or Z series for job {job_id or ''} ({job_name or ''}), skipping 3D plot.")
        return

    # Convert to numpy arrays if needed
    import numpy as np
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)

    # Create a 3D scatter plot
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=x,
                y=y,
                z=z,
                mode="markers+lines",
                marker=dict(
                    size=6,
                    color=z,  # Color by altitude for visual interest
                    colorscale="Viridis",
                    opacity=0.8,
                    colorbar=dict(title="Altitude (m)"),
                ),
            )
        ]
    )

    title = "3D Flight Path"
    if job_name:
        title += f" - {job_name}"
    elif job_id:
        title += f" - {job_id}"

    fig.update_layout(
        title=title,
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)"),
    )

    # Add plotly metric
    (
        metrics_writer.add_plotly_metric(title)
        .with_description("Interactive 3D visualization of the flight path from batch metrics")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_plotly_data(str(fig.to_json()))
    ) 