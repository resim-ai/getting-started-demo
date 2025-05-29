import json
import logging
import os
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

    # Read the flight data from the input JSON file
    input_file = "/tmp/resim/inputs/flight_log.json"
    try:
        with open(input_file, "r") as f:
            flight_data = json.load(f)
        print(f"Successfully loaded flight data from {input_file}")
    except FileNotFoundError:
        print(f"Error: Could not find input file at {input_file}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
        return

    # Write the flight data to the output log
    with open("/tmp/resim/outputs/processed_flight_log.json", "w") as f:
        json.dump(flight_data, f, indent=2)

    print("Completed writing flight data. Exiting.")


if __name__ == "__main__":
    main()
