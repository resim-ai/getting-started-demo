import json
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import plotly.graph_objects as go  # type: ignore
from resim.metrics.fetch_job_metrics import fetch_job_metrics_by_batch
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
from resim.metrics.python.metrics import (  # type: ignore[attr-defined, import]
    DoubleFailureDefinition,
    DoubleOverTimeMetric,
    HistogramBucket,
    MetricImportance,
    MetricStatus,
    PlotlyMetric,
    ScalarMetric,
    SeriesMetricsData,
    StatesOverTimeMetric,
    TextMetric,
    Timestamp,
)
from resim.metrics.python.metrics_writer import ResimMetricsWriter

BATCH_METRICS_CONFIG_PATH = Path("/tmp/resim/inputs/batch_metrics_config.json")


def read_flight_data(filename: str) -> dict:
    """Read and parse flight data from a JSON file.

    Args:
        filename: Path to the flight log JSON file

    Returns:
        dict: Parsed flight data containing metadata and samples
    """
    input_path = Path("/tmp/resim/inputs") / filename
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
        elif sample["status"] == "Warning":
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
        elif sample["status"] == "Warning":
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


def add_plotly_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    """Create and add a 3D visualization of the flight path using Plotly."""
    # Create a 3D scatter plot of the flight path
    x = [sample["position"]["x"] for sample in flight_data["samples"]]
    y = [sample["position"]["y"] for sample in flight_data["samples"]]
    z = [sample["position"]["z"] for sample in flight_data["samples"]]
    states = [sample["state"] for sample in flight_data["samples"]]

    # Map states to numeric values for coloring
    unique_states = list(set(states))
    state_to_num = {state: i for i, state in enumerate(unique_states)}
    color_values = [state_to_num[state] for state in states]

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
    # Create a summary text
    total_time = len(flight_data["samples"])
    states = set(sample["state"] for sample in flight_data["samples"])
    max_speed = max(sample["speed"] for sample in flight_data["samples"])

    summary = f"""# Flight Summary
- Total Duration: {total_time} seconds
- States Observed: {', '.join(states)}
- Maximum Speed: {max_speed:.2f} m/s
- Units: {flight_data['metadata']['units']}
"""

    # Add text metric
    (
        metrics_writer.add_text_metric("Flight Summary")
        .with_description("Summary of the flight data")
        .with_importance(MetricImportance.MEDIUM_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_text(summary)
    )


def main():
    """Entry point for the metrics reader script."""
    print("Starting metrics reader...")
    if BATCH_METRICS_CONFIG_PATH.exists():
        print("Running batch metrics...")
        run_batch_metrics()
    else:
        print("Running test metrics...")
        run_test_metrics()


def run_test_metrics():
    """Process and generate metrics for a single test run."""
    try:
        # Read flight data
        flight_data = read_flight_data("/tmp/resim/inputs/logs/flight_log.json")

        # Create metrics writer with a unique ID for test metrics
        metrics_writer = ResimMetricsWriter(uuid.uuid4())

        # Keep track of metric names we've added
        added_metrics = set()

        def log_metric_addition(name: str) -> None:
            if name in added_metrics:
                print(f"WARNING: Metric name '{name}' is being added again!")
            else:
                print(f"Adding metric: {name}")
                added_metrics.add(name)

        # Add all types of metrics
        log_metric_addition("Maximum Speed")
        add_scalar_metrics(metrics_writer, flight_data)

        log_metric_addition("Speed Over Time")
        add_speed_over_time_plot(metrics_writer, flight_data)

        log_metric_addition("Altitude Over Time")
        add_altitude_warning_plot(metrics_writer, flight_data)

        log_metric_addition("Flight States Over Time")
        add_states_over_time_plot(metrics_writer, flight_data)

        log_metric_addition("X Position Over Time")
        add_position_over_time_plot(metrics_writer, flight_data)

        log_metric_addition("Speed Distribution")
        add_speed_distribution_plot(metrics_writer, flight_data)

        log_metric_addition("3D Flight Path")
        add_plotly_metrics(metrics_writer, flight_data)

        log_metric_addition("Flight Summary")
        add_text_metrics(metrics_writer, flight_data)

        # Write and validate metrics
        print("\nValidating metrics...")
        metrics_proto = metrics_writer.write()

        # Debug: Print all metric names in the proto
        print("\nActual metrics in proto:")
        for metric in metrics_proto.metrics_msg.metrics_data:
            print(f"Proto metric name: '{metric.name}'")

        validate_job_metrics(metrics_proto.metrics_msg)

        # Write to file
        output_path = Path("/tmp/resim/outputs/metrics.binproto")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("wb") as metrics_out:
            metrics_out.write(metrics_proto.metrics_msg.SerializeToString())
        print(f"Wrote metrics to {output_path}")

    except Exception as e:
        print(f"Error details: {str(e)}")  # Add detailed error logging
        raise RuntimeError("Error processing metrics") from e

    print("Completed processing metrics. Exiting.")


def run_batch_metrics():
    """Process and generate aggregate metrics for a batch of tests."""
    try:
        # Read batch config
        with open(BATCH_METRICS_CONFIG_PATH, "r") as f:
            config = json.load(f)

        # Create metrics writer with a unique ID for batch metrics
        metrics_writer = ResimMetricsWriter(uuid.uuid4())

        # Get all test metrics for this batch
        test_metrics = fetch_job_metrics_by_batch(
            token=config["authToken"],
            api_url=config["apiURL"],
            batch_id=uuid.UUID(config["batchID"]),
            project_id=uuid.UUID(config["projectID"]),
        )

        # Calculate batch-level metrics
        all_max_values = []
        print(test_metrics)
        for test_metric in test_metrics.values():
            # Extract max value from each test's metrics
            for metric in test_metric.metrics:
                print(metric.name)
                if metric.name == "Maximum Random Value":
                    scalar_metric: ScalarMetric = metric  # type: ignore
                    all_max_values.append(scalar_metric.value)

        # Create batch-level metrics
        if all_max_values:
            batch_max = max(all_max_values)
            batch_avg = sum(all_max_values) / len(all_max_values)

            # Add batch-level scalar metrics
            (
                metrics_writer.add_scalar_metric("Batch Maximum Value")
                .with_description("Maximum value across all tests")
                .with_importance(MetricImportance.HIGH_IMPORTANCE)
                .with_value(batch_max)
                .with_status(MetricStatus.PASSED_METRIC_STATUS)
            )

            (
                metrics_writer.add_scalar_metric("Batch Average Maximum")
                .with_description("Average of maximum values across tests")
                .with_importance(MetricImportance.MEDIUM_IMPORTANCE)
                .with_value(batch_avg)
                .with_status(MetricStatus.PASSED_METRIC_STATUS)
            )

        # Write and validate metrics
        metrics_proto = metrics_writer.write()
        validate_job_metrics(metrics_proto.metrics_msg)

        # Write to file
        output_path = Path("/tmp/resim/outputs/metrics.binproto")
        with output_path.open("wb") as metrics_out:
            metrics_out.write(metrics_proto.metrics_msg.SerializeToString())
        print(f"Batch metrics: Wrote metrics to {output_path}")  # Debug log

    except Exception as e:
        raise RuntimeError("Error processing batch metrics") from e

    print("Completed processing batch metrics. Exiting.")


if __name__ == "__main__":
    main()
