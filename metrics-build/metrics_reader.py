import uuid
from pathlib import Path
from datetime import datetime
from resim.metrics.python.metrics_writer import ResimMetricsWriter
from resim.metrics.python.metrics import (
    Timestamp,
    DoubleFailureDefinition,
    SeriesMetricsData,
    MetricStatus,
    MetricImportance,
    TimestampType,
    HistogramMetric,
    HistogramBucket,
    ScalarMetric,
    DoubleOverTimeMetric,
    StatesOverTimeMetric,
    LinePlotMetric,
    BarChartMetric,
    PlotlyMetric,
    TextMetric,
    ImageMetric,
    ImageListMetric,
    ExternalFileMetricsData
)
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
import numpy as np
from typing import Tuple, List, Dict
import json
import plotly.express as px
import plotly.graph_objects as go
from resim.metrics.fetch_job_metrics import fetch_job_metrics_by_batch

BATCH_METRICS_CONFIG_PATH = Path("/tmp/resim/inputs/batch_metrics_config.json")

def read_all_values(filename: str) -> Tuple[list[Timestamp], list[float]]:
    values = []
    timestamps = []
    with open(filename, 'r') as f:
        for i, line in enumerate(f.readlines()):
            timestamp_str, value_str = line.strip().split(',')
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
            base_secs = int(dt.timestamp())
            # Space timestamps 1 second apart to have a longer timespan
            timestamps.append(Timestamp(secs=base_secs + i, nanos=0))
            values.append(float(value_str))
    return timestamps, values

def read_flight_data(filename: str) -> dict:
    with open(filename, 'r') as f:
        return json.load(f)

def add_scalar_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    # Maximum speed metric
    max_speed = max(sample["speed"] for sample in flight_data["samples"])
    metrics_writer.add_scalar_metric("Maximum Speed")\
        .with_description("Maximum speed achieved during flight")\
        .with_importance(MetricImportance.HIGH_IMPORTANCE)\
        .with_value(max_speed)\
        .with_unit("m/s")\
        .with_status(MetricStatus.PASSED_METRIC_STATUS)

def add_double_over_time_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    # Extract speed data over time
    timestamps = []
    speeds = []
    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace('Z', '+00:00'))
        timestamps.append(Timestamp(secs=int(dt.timestamp()), nanos=0))
        speeds.append(sample["speed"])

    # Create series data
    timestamps_data = SeriesMetricsData("Timestamps", series=np.array(timestamps))
    speeds_data = SeriesMetricsData(
        "Speed",
        series=np.array(speeds),
        unit="m/s",
        index_data=timestamps_data
    )
    statuses_data = SeriesMetricsData(
        "Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(speeds)),
        index_data=timestamps_data
    )

    # Add speed over time metric
    metrics_writer.add_double_over_time_metric("Speed Over Time")\
        .with_description("Speed measurements over time")\
        .with_importance(MetricImportance.HIGH_IMPORTANCE)\
        .with_status(MetricStatus.PASSED_METRIC_STATUS)\
        .with_y_axis_name("Speed (m/s)")\
        .with_doubles_over_time_data([speeds_data])\
        .with_statuses_over_time_data([statuses_data])

def add_states_over_time_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    # Extract state data over time
    timestamps = []
    states = []
    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace('Z', '+00:00'))
        timestamps.append(Timestamp(secs=int(dt.timestamp()), nanos=0))
        states.append(sample["state"])

    # Create series data
    timestamps_data = SeriesMetricsData("Timestamps", series=np.array(timestamps))
    states_data = SeriesMetricsData(
        "States",
        series=np.array(states),
        index_data=timestamps_data
    )
    statuses_data = SeriesMetricsData(
        "Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(states)),
        index_data=timestamps_data
    )

    # Get unique states
    states_set = set(sample["state"] for sample in flight_data["samples"])
    failure_states = {"Warning"}  # Example: consider Warning states as failures

    # Add states over time metric
    metrics_writer.add_states_over_time_metric("Flight States Over Time")\
        .with_description("Flight state transitions over time")\
        .with_importance(MetricImportance.HIGH_IMPORTANCE)\
        .with_status(MetricStatus.PASSED_METRIC_STATUS)\
        .with_states_over_time_data([states_data])\
        .with_statuses_over_time_data([statuses_data])\
        .with_states_set(states_set)\
        .with_failure_states(failure_states)

def add_line_plot_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    # Extract position data
    timestamps = []
    x_positions = []
    y_positions = []
    z_positions = []
    
    for sample in flight_data["samples"]:
        dt = datetime.fromisoformat(sample["timestamp"].replace('Z', '+00:00'))
        timestamps.append(Timestamp(secs=int(dt.timestamp()), nanos=0))
        x_positions.append(sample["position"]["x"])
        y_positions.append(sample["position"]["y"])
        z_positions.append(sample["position"]["z"])

    # Create series data
    timestamps_data = SeriesMetricsData("Timestamps", series=np.array(timestamps))
    x_data = SeriesMetricsData("X Position", series=np.array(x_positions), unit="m", index_data=timestamps_data)
    y_data = SeriesMetricsData("Y Position", series=np.array(y_positions), unit="m", index_data=timestamps_data)
    z_data = SeriesMetricsData("Z Position", series=np.array(z_positions), unit="m", index_data=timestamps_data)
    statuses_data = SeriesMetricsData(
        "Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(timestamps)),
        index_data=timestamps_data
    )

    # Add position over time metric
    metrics_writer.add_line_plot_metric("Position Over Time")\
        .with_description("3D position over time")\
        .with_importance(MetricImportance.HIGH_IMPORTANCE)\
        .with_status(MetricStatus.PASSED_METRIC_STATUS)\
        .with_x_axis_name("Time")\
        .with_y_axis_name("Position (m)")\
        .with_x_doubles_data([timestamps_data, timestamps_data, timestamps_data])\
        .with_y_doubles_data([x_data, y_data, z_data])\
        .with_statuses_data([statuses_data, statuses_data, statuses_data])\
        .with_legend_series_names(["X", "Y", "Z"])

def add_histogram_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    # Extract speed data for histogram
    speeds = [sample["speed"] for sample in flight_data["samples"]]
    
    # Create series data
    speeds_data = SeriesMetricsData("Speeds", series=np.array(speeds), unit="m/s")
    statuses_data = SeriesMetricsData(
        "Statuses",
        series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(speeds))
    )

    # Define histogram buckets
    max_speed = max(speeds)
    bucket_size = max_speed / 10  # 10 buckets
    buckets = [
        HistogramBucket(i * bucket_size, (i + 1) * bucket_size)
        for i in range(10)
    ]

    # Add speed histogram metric
    metrics_writer.add_histogram_metric("Speed Distribution")\
        .with_description("Distribution of speeds during flight")\
        .with_importance(MetricImportance.MEDIUM_IMPORTANCE)\
        .with_status(MetricStatus.PASSED_METRIC_STATUS)\
        .with_values_data(speeds_data)\
        .with_statuses_data(statuses_data)\
        .with_buckets(buckets)\
        .with_lower_bound(0.0)\
        .with_upper_bound(max_speed)

def add_plotly_metrics(metrics_writer: ResimMetricsWriter, flight_data: dict) -> None:
    # Create a 3D scatter plot of the flight path
    x = [sample["position"]["x"] for sample in flight_data["samples"]]
    y = [sample["position"]["y"] for sample in flight_data["samples"]]
    z = [sample["position"]["z"] for sample in flight_data["samples"]]
    states = [sample["state"] for sample in flight_data["samples"]]

    fig = go.Figure(data=[go.Scatter3d(
        x=x, y=y, z=z,
        mode='markers+lines',
        marker=dict(
            size=6,
            color=states,
            colorscale='Viridis',
            opacity=0.8
        )
    )])

    fig.update_layout(
        title='3D Flight Path',
        scene=dict(
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            zaxis_title='Z (m)'
        )
    )

    metrics_writer.add_plotly_metric("3D Flight Path")\
        .with_description("Interactive 3D visualization of the flight path")\
        .with_importance(MetricImportance.HIGH_IMPORTANCE)\
        .with_status(MetricStatus.PASSED_METRIC_STATUS)\
        .with_plotly_data(fig.to_json())

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

    metrics_writer.add_text_metric("Flight Summary")\
        .with_description("Summary of the flight data")\
        .with_importance(MetricImportance.MEDIUM_IMPORTANCE)\
        .with_status(MetricStatus.PASSED_METRIC_STATUS)\
        .with_text(summary)

def main():
    print("Starting metrics reader...")
    if BATCH_METRICS_CONFIG_PATH.exists():
        print("Running batch metrics...")
        run_batch_metrics()
    else:
        print("Running test metrics...")
        run_test_metrics()   

def run_test_metrics():
    try:
        # Read flight data
        flight_data = read_flight_data('/tmp/resim/inputs/logs/test.log')
        
        # Create metrics writer
        metrics_writer = ResimMetricsWriter(uuid.uuid4())
        
        # Add all types of metrics
        add_scalar_metrics(metrics_writer, flight_data)
        add_double_over_time_metrics(metrics_writer, flight_data)
        add_states_over_time_metrics(metrics_writer, flight_data)
        add_line_plot_metrics(metrics_writer, flight_data)
        add_histogram_metrics(metrics_writer, flight_data)
        add_plotly_metrics(metrics_writer, flight_data)
        add_text_metrics(metrics_writer, flight_data)
        
        # Write and validate metrics
        metrics_proto = metrics_writer.write()
        validate_job_metrics(metrics_proto.metrics_msg)
        
        # Write to file
        output_path = Path('/tmp/resim/outputs/metrics.binproto')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open("wb") as metrics_out:
            metrics_out.write(metrics_proto.metrics_msg.SerializeToString())
        print(f"Wrote metrics to {output_path}")

    except Exception as e:
        raise RuntimeError("Error processing metrics") from e
    
    print("Completed processing metrics. Exiting.")

def run_batch_metrics():
    try:
        # Read batch config
        with open(BATCH_METRICS_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            
        # Create metrics writer
        metrics_writer = ResimMetricsWriter(uuid.uuid4())
        
        # Get all test metrics for this batch
        test_metrics = fetch_job_metrics_by_batch(
            token=config["authToken"],
            api_url=config["apiURL"],
            batch_id=uuid.UUID(config["batchID"]),
            project_id=uuid.UUID(config["projectID"])
        )
        
        # Calculate batch-level metrics
        all_max_values = []
        print(test_metrics)
        for test_metric in test_metrics.values():
            # Extract max value from each test's metrics
            for metric in test_metric.metrics:
                print(metric.name)
                if metric.name == "Maximum Random Value":
                    scalar_metric: ScalarMetric = metric # type: ignore
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
        output_path = Path('/tmp/resim/outputs/metrics.binproto')
        with output_path.open("wb") as metrics_out:
            metrics_out.write(metrics_proto.metrics_msg.SerializeToString())
        print(f"Batch metrics: Wrote metrics to {output_path}")  # Debug log
            
    except Exception as e:
        raise RuntimeError("Error processing batch metrics") from e
    
    print("Completed processing batch metrics. Exiting.")

if __name__ == "__main__":
    main() 
