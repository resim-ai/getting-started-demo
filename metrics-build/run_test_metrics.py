import uuid
from pathlib import Path

from metrics_builder import (add_altitude_warning_plot,
                             add_plotly_metrics_from_flight_data,
                             add_position_over_time_plot, add_scalar_metrics,
                             add_speed_distribution_plot,
                             add_speed_over_time_plot,
                             add_states_over_time_plot, add_text_metrics,
                             read_flight_data)
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
from resim.metrics.python.metrics_writer import ResimMetricsWriter


def run_test_metrics():
    """Process and generate metrics for a single test run."""
    try:
        # Read flight data
        flight_data = read_flight_data("processed_flight_log.json")

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
        add_plotly_metrics_from_flight_data(metrics_writer, flight_data)

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


if __name__ == "__main__":
    run_test_metrics() 