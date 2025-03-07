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
    TimestampType
)
from resim.metrics.proto.validate_metrics_proto import validate_job_metrics
import numpy as np
from typing import Tuple
from resim.metrics.python.metrics_utils import TimestampType

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
        # we haven't got any :(
    else:
        print("Running test metrics...")
        run_test_metrics()   

def run_test_metrics():
    try:
        metrics_writer = ResimMetricsWriter(uuid.uuid4())
        
        timestamps, values = read_all_values('/tmp/resim/inputs/logs/test.log')
        print(f"Read {len(values)} values")
        
        # Create the metrics data
        timestamps_data = SeriesMetricsData(
            "Timestamps",
            series=np.array(timestamps)
        )
        
        values_series = SeriesMetricsData(
            "Random Values",
            series=np.array(values), 
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
        
        # Write and validate metrics
        metrics_proto = metrics_writer.write()
        
        # Just call validate_job_metrics - it will raise an exception if invalid
        validate_job_metrics(metrics_proto.metrics_msg)
        print("Metrics validation passed")
        
        # Write to file if validation passed
        output_path = Path('/tmp/resim/outputs/metrics.binproto')
        with output_path.open("wb") as metrics_out:
            metrics_out.write(metrics_proto.metrics_msg.SerializeToString())
            
    except Exception as e:
        raise RuntimeException("Error processing metrics") from e # Re-raise the exception to ensure the container exits with error
    
    print("Completed processing values. Exiting.")

if __name__ == "__main__":
    main() 