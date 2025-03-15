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
    ScalarMetric
)
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
import numpy as np
from typing import Tuple
from resim.metrics.python.metrics_utils import TimestampType
import json
from resim.metrics.fetch_job_metrics import fetch_job_metrics_by_batch
import plotly.express as px

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
        metrics_writer = ResimMetricsWriter(uuid.uuid4())
        timestamps, values = read_all_values('/tmp/resim/inputs/logs/test.log')
        values_array = np.array(values)
        print(f"Read {len(values)} values")
        
        # Create series metrics data
        timestamps_data = SeriesMetricsData(
            "Timestamps",
            series=np.array(timestamps)
        )
        
        values_series = SeriesMetricsData(
            "Random Values",
            series=values_array, 
            index_data=timestamps_data
        )

        statuses_series = SeriesMetricsData(
            "Random Values Statuses",
            series=np.array([MetricStatus.PASSED_METRIC_STATUS] * len(values)),
            index_data=timestamps_data
        )
        
        # Create and store the metric
        metrics_before_proto_write = (metrics_writer.add_double_over_time_metric("Random Values Over Time") 
            .with_description("Random values from test log over time") 
            .with_blocking(False) 
            .with_should_display(True) 
            .with_importance(MetricImportance.HIGH_IMPORTANCE) 
            .with_status(MetricStatus.PASSED_METRIC_STATUS) 
            .with_y_axis_name("Value") 
            .with_failure_definitions([
                DoubleFailureDefinition(fails_below=0, fails_above=100)
            ]) 
            .with_doubles_over_time_data([values_series])
            .with_statuses_over_time_data([statuses_series])
        )
        
        # 2. Add histogram

        # Define histogram buckets (e.g., 10 buckets between 0 and 100)
        bucket_size = 10
        buckets = [
            HistogramBucket(i, i + bucket_size)
            for i in range(0, 100, bucket_size)
        ]

        # Create histogram metric with explicit buckets
        histogram_metric = metrics_writer.add_histogram_metric("Random Values Histogram")\
            .with_description("Distribution of random values")\
            .with_importance(MetricImportance.MEDIUM_IMPORTANCE)\
            .with_status(MetricStatus.PASSED_METRIC_STATUS) 

        # Add the data to the histogram metric
        histogram_metric.with_values_data(values_series)\
            .with_statuses_data(statuses_series)\
            .with_buckets(buckets)\
            .with_lower_bound(0.0)\
            .with_upper_bound(100.0)

        # 3. Add plotly scatter visualization
        fig = px.scatter(
            x=range(len(values)), 
            y=values,
            title="Random Values Scatter Plot",
            labels={'x': 'Sample Number', 'y': 'Value'}
        )
        metrics_writer.add_plotly_metric("Random Values Plotly")\
            .with_description("Scatter plot of random values")\
            .with_plotly_data(str(fig.to_json()))\
            .with_importance(MetricImportance.HIGH_IMPORTANCE)\
            .with_status(MetricStatus.PASSED_METRIC_STATUS) 

        # 4. Add scalar metrics (test level)
        max_value = np.max(values_array)
        metrics_writer.add_scalar_metric("Maximum Random Value")\
            .with_description("Maximum value generated in this test")\
            .with_importance(MetricImportance.HIGH_IMPORTANCE)\
            .with_value(max_value)\
            .with_status(MetricStatus.PASSED_METRIC_STATUS) 
        
        # Write metrics to the correct location
        metrics_proto = metrics_writer.write()
        validate_job_metrics(metrics_proto.metrics_msg)
        print("Metrics validation passed")
        
        # Make sure to write to /tmp/resim/outputs/metrics.binproto
        output_path = Path('/tmp/resim/outputs/metrics.binproto')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open("wb") as metrics_out:
            metrics_out.write(metrics_proto.metrics_msg.SerializeToString())
        print(f"Test metrics: Wrote metrics to {output_path}")  # Debug log

    except Exception as e:
        raise RuntimeError("Error processing test metrics") from e
    
    print("Completed processing values. Exiting.")

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