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

def read_last_line(filename: str) -> float:
    with open(filename, 'r') as f:
        lines = f.readlines()
        if lines:
            # Format: "2024-03-21 12:34:56,75.32"
            return float(lines[-1].strip().split(',')[1])
    return 0.0

def main():
    print("Starting metrics reader...")
    
    for i in range(100):
        try:
            # Create new metrics writer for each iteration
            metrics_writer = ResimMetricsWriter(uuid.uuid4())
            
            # Read the latest value
            value = read_last_line('/tmp/resim/inputs/logs/test.log')
            print(f"Reading value {i+1}/100: {value}") 
            
            # Create metric
            metrics_writer.add_scalar_metric("Random Value") \
                .with_failure_definition(
                    DoubleFailureDefinition(fails_above=100, fails_below=0)
                ) \
                .with_value(value) \
                .with_description("Random value from test log") \
                .with_blocking(False) \
                .with_should_display(True) \
                .with_importance(MetricImportance.HIGH_IMPORTANCE) \
                .with_status(MetricStatus.PASSED_METRIC_STATUS)
            
            # Write metric
            metrics_proto = metrics_writer.write()
            output_path = Path('/tmp/resim/outputs/metrics.binproto')
            with open(output_path, 'wb') as f:
                f.write(metrics_proto.metrics_msg.SerializeToString())
            print(f"Wrote metric {i+1}/100")
                
        except Exception as e:
            print(f"Error processing metrics: {e}")
    
    print("Completed processing 100 values. Exiting.")

if __name__ == "__main__":
    main() 