import json
import os
from datetime import datetime
from resim.sdk.metrics.emissions import Emitter

# Ensure the outputs directory exists
os.makedirs("/tmp/resim/outputs/", exist_ok=True)


def main():
    print("Starting simulation run...")

    # Read the test_config.json file to get the experience location
    config_path = "/tmp/resim/test_config.json"
    try:
        with open(config_path, "r") as f:
            test_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find config file at {config_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        return

    experience_location = test_config["experienceLocation"]
    print(f"Experience location: {experience_location}")

    # Read the flight_log.json directly from the experience location
    src_flight_log = os.path.join(experience_location, "flight_log.json")
    try:
        with open(src_flight_log, "r") as f:
            flight_data = json.load(f)
        print(f"Successfully loaded flight data from {src_flight_log}")
    except FileNotFoundError:
        print(f"Error: Could not find flight log at {src_flight_log}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in flight log: {e}")
        return

    # Validate flight data structure
    if "samples" not in flight_data:
        print("Error: Flight log must contain 'samples' key")
        return

    samples = flight_data.get("samples", [])
    if not samples:
        print("Warning: Flight log contains no samples")
        return

    # Parse timestamps and convert to nanoseconds (relative to first timestamp)
    timestamps = []
    first_timestamp_ns = None

    for sample in samples:
        if "timestamp" not in sample:
            print("Error: Sample missing 'timestamp' field")
            return
        
        # Parse ISO 8601 timestamp
        dt = datetime.fromisoformat(sample["timestamp"])
        timestamp_ns = int(dt.timestamp() * 1e9)
        
        if first_timestamp_ns is None:
            first_timestamp_ns = timestamp_ns
        
        # Calculate relative timestamp
        relative_timestamp = timestamp_ns - first_timestamp_ns
        timestamps.append(relative_timestamp)

    # Extract data arrays for each topic
    speeds = [sample.get("speed", 0.0) for sample in samples]
    positions_x = [sample.get("position", {}).get("x", 0.0) for sample in samples]
    positions_y = [sample.get("position", {}).get("y", 0.0) for sample in samples]
    positions_z = [sample.get("position", {}).get("z", 0.0) for sample in samples]
    states = [sample.get("state", "") for sample in samples]
    statuses = [sample.get("status", "") for sample in samples]

    # Emit data using Metrics 2.0 Emitter
    config_path = ".resim/metrics/config.yml"
    output_path = "/tmp/resim/outputs/emissions.resim.jsonl"
    
    with Emitter(config_path=config_path, output_path=output_path) as emitter:
        # Emit speed data
        emitter.emit_series("drone_speed", {"speed": speeds}, timestamps=timestamps)
        
        # Emit position data
        emitter.emit_series(
            "drone_position",
            {"x": positions_x, "y": positions_y, "z": positions_z},
            timestamps=timestamps
        )
        
        # Emit state data
        emitter.emit_series("drone_state", {"state": states}, timestamps=timestamps)
        
        # Emit status data
        emitter.emit_series("drone_status", {"status": statuses}, timestamps=timestamps)

    print(f"Completed emitting flight data to {output_path}. Exiting.")


if __name__ == "__main__":
    main()
