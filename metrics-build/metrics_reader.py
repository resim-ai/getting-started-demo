import json
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import plotly.graph_objects as go  # type: ignore
from resim.metrics.fetch_job_metrics import fetch_job_metrics_by_batch
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
from resim.metrics.python.metrics import (
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
    """Read and parse flight data from a JSON file."""
    with open(filename, "r") as f:
        return json.load(f)


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


def add_double_over_time_metrics(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Add time series metrics for speed measurements over time."""
    # Extract speed data over time
    timestamps = []
    speeds = []
    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
        timestamps.append(Timestamp(secs=int(dt.timestamp()), nanos=0))
        speeds.append(sample["speed"])

    # Create series data
    timestamps_data = SeriesMetricsData("Speed_Timestamps", series=np.array(timestamps))
    speeds_data = SeriesMetricsData(
        "Speed_Values", series=np.array(speeds), unit="m/s", index_data=timestamps_data
    )
    statuses_data = SeriesMetricsData(
        "Speed_Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(speeds)),
        index_data=timestamps_data,
    )

    # Create failure definitions (one per data series)
    failure_defs = [DoubleFailureDefinition(0.0, 100.0)]

    # Add speed over time metric
    (
        metrics_writer.add_double_over_time_metric("Speed Over Time")
        .with_description("Speed measurements over time")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_y_axis_name("Speed (m/s)")
        .with_doubles_over_time_data([speeds_data])
        .with_statuses_over_time_data([statuses_data])
        .with_failure_definitions(failure_defs)
    )


def add_states_over_time_metrics(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Add time series metrics for flight state transitions."""
    # Extract state data over time
    timestamps = []
    states = []
    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))
        timestamps.append(Timestamp(secs=int(dt.timestamp()), nanos=0))
        states.append(sample["state"])

    # Create series data
    timestamps_data = SeriesMetricsData(
        "States_Timestamps", series=np.array(timestamps)
    )
    states_data = SeriesMetricsData(
        "States_Values", series=np.array(states), index_data=timestamps_data
    )
    statuses_data = SeriesMetricsData(
        "States_Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(states)),
        index_data=timestamps_data,
    )

    # Get unique states and ensure they're strings
    states_set = {str(sample["state"]) for sample in flight_data["samples"]}
    failure_states: set[str] = set()  # No failure states for now

    # Add states over time metric
    (
        metrics_writer.add_states_over_time_metric("Flight States Over Time")
        .with_description("Flight state transitions over time")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_states_over_time_data([states_data])
        .with_statuses_over_time_data([statuses_data])
        .with_states_set(states_set)
        .with_failure_states(failure_states)
        .with_legend_series_names(["Flight State"])
    )


def add_line_plot_metrics(
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

    # Create series data using doubles for both axes
    x_data = SeriesMetricsData("Position_Time", series=np.array(x_values), unit="s")
    y_data = SeriesMetricsData("Position_Values", series=np.array(y_values), unit="m")
    statuses_data = SeriesMetricsData(
        "Position_Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(x_values)),
    )

    # Add position over time metric
    metric = (
        metrics_writer.add_line_plot_metric("X Position Over Time")
        .with_description("X-axis position over time")
        .with_importance(MetricImportance.HIGH_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_x_axis_name("Time (s)")
        .with_y_axis_name("X Position (m)")
        .with_legend_series_names(["Position"])
    )

    # Set the data using direct attribute assignment
    metric.x_doubles_data = [x_data]
    metric.y_doubles_data = [y_data]
    metric.statuses_data = [statuses_data]


def add_histogram_metrics(
    metrics_writer: ResimMetricsWriter, flight_data: dict
) -> None:
    """Create and add a histogram showing the distribution of flight speeds."""
    # Extract speed data for histogram
    speeds = [sample["speed"] for sample in flight_data["samples"]]

    # Create series data
    speeds_data = SeriesMetricsData(
        "Histogram_Speed_Values", series=np.array(speeds), unit="m/s"
    )
    statuses_data = SeriesMetricsData(
        "Histogram_Speed_Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(speeds)),
    )

    # Define histogram buckets
    max_speed = max(speeds)
    bucket_size = max_speed / 10  # 10 buckets
    buckets = [
        HistogramBucket(i * bucket_size, (i + 1) * bucket_size) for i in range(10)
    ]

    # Add speed histogram metric
    (
        metrics_writer.add_histogram_metric("Speed Distribution")
        .with_description("Distribution of speeds during flight")
        .with_importance(MetricImportance.MEDIUM_IMPORTANCE)
        .with_status(MetricStatus.PASSED_METRIC_STATUS)
        .with_values_data(speeds_data)
        .with_statuses_data(statuses_data)
        .with_buckets(buckets)
        .with_lower_bound(0.0)
        .with_upper_bound(max_speed)
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
        flight_data = read_flight_data("/tmp/resim/inputs/logs/test.log")

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
        add_double_over_time_metrics(metrics_writer, flight_data)

        log_metric_addition("Flight States Over Time")
        add_states_over_time_metrics(metrics_writer, flight_data)

        log_metric_addition("X Position Over Time")
        add_line_plot_metrics(metrics_writer, flight_data)

        log_metric_addition("Speed Distribution")
        add_histogram_metrics(metrics_writer, flight_data)

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
