import json
import logging
import os
import shutil
from datetime import datetime

# Ensure the outputs directory exists
os.makedirs("/tmp/resim/outputs/", exist_ok=True)

# Set up logging
logging.basicConfig(
    filename="/tmp/resim/outputs/processed_flight_log.json",
    level=logging.INFO,
    format="%(message)s",  # We'll just log the raw JSON data
    datefmt="%Y-%m-%d %H:%M:%S",
)


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

    # Write the flight data to the output log
    with open("/tmp/resim/outputs/processed_flight_log.json", "w") as f:
        json.dump(flight_data, f, indent=2)

    print("Completed writing flight data. Exiting.")


if __name__ == "__main__":
    main()
