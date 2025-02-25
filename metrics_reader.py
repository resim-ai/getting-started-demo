import uuid
from pathlib import Path
from resim.metrics.python.metrics_writer import ResimMetricsWriter
from resim.metrics.python.metrics import (
    Timestamp,
    DoubleFailureDefinition,
    SeriesMetricsData,
    MetricStatus,
    MetricImportance
)
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics

def read_all_values(filename: str) -> list:
    values = []
    timestamps = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            timestamp_str, value_str = line.strip().split(',')
            timestamps.append(Timestamp.from_string(timestamp_str))
            values.append(float(value_str))
    return timestamps, values

def main():
    print("Starting metrics reader...")
    
    try:
        metrics_writer = ResimMetricsWriter(uuid.uuid4())
        
        timestamps, values = read_all_values('/tmp/resim/inputs/logs/test.log')
        print(f"Read {len(values)} values")
        
        time_series = SeriesMetricsData("Random Values")
        for t, v in zip(timestamps, values):
            time_series.add_element(t, v)
        
        metrics_writer.add_double_over_time_metric("Random Values Over Time") \
            .with_doubles_over_time_data([time_series]) \
            .with_failure_definitions([
                DoubleFailureDefinition(fails_above=100, fails_below=0)
            ]) \
            .with_description("Random values from test log over time") \
            .with_blocking(False) \
            .with_should_display(True) \
            .with_importance(MetricImportance.HIGH_IMPORTANCE) \
            .with_status(MetricStatus.PASSED_METRIC_STATUS) \
            .with_y_axis_name("Value")
        
        # Write and validate metrics
        metrics_proto = metrics_writer.write()
        
        # Validate the metrics message
        validation_result = validate_job_metrics(metrics_proto.metrics_msg)
        if not validation_result.valid:
            raise ValueError(f"Invalid metrics proto: {validation_result.message}")
        print("Metrics validation passed")
        
        # Write to file if validation passed
        output_path = Path('/tmp/resim/outputs/metrics.binproto')
        with open(output_path, 'wb') as f:
            f.write(metrics_proto.metrics_msg.SerializeToString())
        print("Wrote time series metric")
            
    except Exception as e:
        print(f"Error processing metrics: {e}")
        raise  # Re-raise the exception to ensure the container exits with error
    
    print("Completed processing values. Exiting.")

if __name__ == "__main__":
    main() 