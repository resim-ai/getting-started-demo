import json
import uuid
from pathlib import Path

from metrics_builder import add_altitude_comparison_plot
from resim.metrics.fetch_job_metrics import fetch_job_metrics_by_batch
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
from resim.metrics.python.metrics import (MetricImportance, MetricStatus,
                                          ScalarMetric)
from resim.metrics.python.metrics_writer import ResimMetricsWriter


def run_batch_metrics():
    """Process and generate aggregate metrics for a batch of tests."""
    try:
        # Read batch config
        with open("/tmp/resim/inputs/batch_metrics_config.json", "r", encoding="utf-8") as metrics_config_file:
            metrics_config = json.load(metrics_config_file)

        token = metrics_config["authToken"]
        api_url = metrics_config["apiURL"]
        batch_id = metrics_config["batchID"]
        project_id = metrics_config["projectID"]

        # Fetch all metrics for the batch (returns a dict: job_id -> metrics proto object)
        job_to_metrics = fetch_job_metrics_by_batch(
            token=token,
            api_url=api_url,
            project_id=project_id,
            batch_id=batch_id,
        )

        max_speeds = []
        error_counts = []
        warning_counts = []
        success_counts = []

        for test_id, metrics_proto in job_to_metrics.items():
            try:
                # Example: Extract max speed from scalar metrics
                max_speed = None
                for metric in metrics_proto.metrics:
                    if metric.name == "Maximum Speed" and isinstance(metric, ScalarMetric):
                        max_speed = metric.value
                        break

                if max_speed is not None:
                    max_speeds.append(max_speed)

                # Count status occurrences
                error_count = sum(
                    1 for metric in metrics_proto.metrics
                    if getattr(metric, "status", None) == MetricStatus.FAIL_BLOCK_METRIC_STATUS
                )
                warning_count = sum(
                    1 for metric in metrics_proto.metrics
                    if getattr(metric, "status", None) == MetricStatus.FAIL_WARN_METRIC_STATUS
                )
                success_count = sum(
                    1 for metric in metrics_proto.metrics
                    if getattr(metric, "status", None) == MetricStatus.PASSED_METRIC_STATUS
                )

                error_counts.append(error_count)
                warning_counts.append(warning_count)
                success_counts.append(success_count)

            except Exception as e:
                print(f"Error processing test {test_id}: {str(e)}")
                continue

        # Calculate batch-level metrics
        if max_speeds:
            avg_max_speed = sum(max_speeds) / len(max_speeds)
            highest_speed = max(max_speeds)

            total_errors = sum(error_counts)
            total_warnings = sum(warning_counts)
            total_successes = sum(success_counts)
            total_samples = total_errors + total_warnings + total_successes

            success_rate = (
                (total_successes / total_samples) * 100 if total_samples > 0 else 0
            )

            metrics_writer = ResimMetricsWriter(uuid.uuid4())

            # Add batch-level scalar metrics
            (
                metrics_writer.add_scalar_metric("Highest Recorded Speed")
                .with_description("Maximum speed achieved across all flights")
                .with_importance(MetricImportance.HIGH_IMPORTANCE)
                .with_value(highest_speed)
                .with_unit("m/s")
                .with_status(MetricStatus.PASSED_METRIC_STATUS)
            )

            (
                metrics_writer.add_scalar_metric("Average Max Speed")
                .with_description("Average of maximum speeds across all flights")
                .with_importance(MetricImportance.HIGH_IMPORTANCE)
                .with_value(avg_max_speed)
                .with_unit("m/s")
                .with_status(MetricStatus.PASSED_METRIC_STATUS)
            )

            (
                metrics_writer.add_scalar_metric("Overall Success Rate")
                .with_description("Percentage of successful flight states")
                .with_importance(MetricImportance.HIGH_IMPORTANCE)
                .with_value(success_rate)
                .with_unit("%")
                .with_status(
                    MetricStatus.FAIL_BLOCK_METRIC_STATUS
                    if success_rate < 70
                    else (
                        MetricStatus.FAIL_WARN_METRIC_STATUS
                        if success_rate < 74
                        else MetricStatus.PASSED_METRIC_STATUS
                    )
                )
            )

            # Add the altitude comparison plot
            add_altitude_comparison_plot(metrics_writer, job_to_metrics)

            # Add a summary text metric
            summary = f"""# Flight Batch Summary
- Total Flights: {len(max_speeds)}
- Highest Speed: {highest_speed:.2f} m/s
- Average Max Speed: {avg_max_speed:.2f} m/s
- Total Errors: {total_errors}
- Total Warnings: {total_warnings}
- Success Rate: {success_rate:.1f}%
"""

            (
                metrics_writer.add_text_metric("Batch Summary")
                .with_description("Summary of all flight data")
                .with_importance(MetricImportance.HIGH_IMPORTANCE)
                .with_status(MetricStatus.PASSED_METRIC_STATUS)
                .with_text(summary)
            )

            # Write and validate metrics
            metrics_proto = metrics_writer.write()
            validate_job_metrics(metrics_proto.metrics_msg)

            # Write to file
            output_path = Path("/tmp/resim/outputs/metrics.binproto")
            with output_path.open("wb") as metrics_out:
                metrics_out.write(metrics_proto.metrics_msg.SerializeToString())
            print(f"Batch metrics: Wrote metrics to {output_path}")

    except Exception as e:
        raise RuntimeError("Error processing batch metrics") from e

    print("Completed processing batch metrics. Exiting.")


if __name__ == "__main__":
    run_batch_metrics() 