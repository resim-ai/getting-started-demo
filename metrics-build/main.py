from pathlib import Path

from run_batch_metrics import run_batch_metrics
from run_test_metrics import run_test_metrics

BATCH_METRICS_CONFIG_PATH = Path("/tmp/resim/inputs/batch_metrics_config.json")

def main():
    """Entry point for the metrics builder script."""
    print("Starting to build metrics...")
    if BATCH_METRICS_CONFIG_PATH.exists():
        print("Running batch metrics...")
        run_batch_metrics()
    else:
        print("Running test metrics...")
        run_test_metrics()


if __name__ == "__main__":
    main() 