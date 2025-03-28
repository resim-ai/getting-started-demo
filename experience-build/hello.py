import json
import logging
import os
from datetime import datetime

# Flight data structure
flight_data = {
    "metadata": {
        "units": {
            "speed": "m/s",
            "position": {"x": "m", "y": "m", "z": "m"},
            "time": "s"
        }
    },
    "samples": [
        # Initial state (0-2s)
        {"timestamp": "2024-03-18T10:00:00", "speed": 0.0, "state": "Idle", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 0.0}},
        {"timestamp": "2024-03-18T10:00:01", "speed": 0.0, "state": "Idle", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 0.0}},
        {"timestamp": "2024-03-18T10:00:02", "speed": 0.0, "state": "Idle", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 0.0}},
        
        # Takeoff (3-7s)
        {"timestamp": "2024-03-18T10:00:03", "speed": 2.0, "state": "Takeoff", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 2.0}},
        {"timestamp": "2024-03-18T10:00:04", "speed": 2.0, "state": "Takeoff", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 4.0}},
        {"timestamp": "2024-03-18T10:00:05", "speed": 2.0, "state": "Takeoff", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 6.0}},
        {"timestamp": "2024-03-18T10:00:06", "speed": 2.0, "state": "Takeoff", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 8.0}},
        {"timestamp": "2024-03-18T10:00:07", "speed": 2.0, "state": "Takeoff", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},

        # Hover at altitude (8-10s)
        {"timestamp": "2024-03-18T10:00:08", "speed": 0.0, "state": "Hovering", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:09", "speed": 0.0, "state": "Hovering", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:10", "speed": 0.0, "state": "Hovering", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},

        # Move forward (11-15s)
        {"timestamp": "2024-03-18T10:00:11", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 2.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:12", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 4.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:13", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 6.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:14", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 8.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:15", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 10.0, "y": 0.0, "z": 10.0}},

        # Turn right and move (16-20s)
        {"timestamp": "2024-03-18T10:00:16", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 10.0, "y": 2.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:17", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 10.0, "y": 4.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:18", "speed": 2.0, "state": "Moving", "status": "Warning", 
         "position": {"x": 10.0, "y": 6.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:19", "speed": 2.0, "state": "Moving", "status": "Warning", 
         "position": {"x": 10.0, "y": 8.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:20", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 10.0, "y": 10.0, "z": 10.0}},

        # Move backward (21-25s)
        {"timestamp": "2024-03-18T10:00:21", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 8.0, "y": 10.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:22", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 6.0, "y": 10.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:23", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 4.0, "y": 10.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:24", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 2.0, "y": 10.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:25", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 0.0, "y": 10.0, "z": 10.0}},

        # Move left to complete square (26-30s)
        {"timestamp": "2024-03-18T10:00:26", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 0.0, "y": 8.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:27", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 0.0, "y": 6.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:28", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 0.0, "y": 4.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:29", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 0.0, "y": 2.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:30", "speed": 2.0, "state": "Moving", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},

        # Hover before descent (31-33s)
        {"timestamp": "2024-03-18T10:00:31", "speed": 0.0, "state": "Hovering", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:32", "speed": 0.0, "state": "Hovering", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},
        {"timestamp": "2024-03-18T10:00:33", "speed": 0.0, "state": "Hovering", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 10.0}},

        # Descent (34-38s)
        {"timestamp": "2024-03-18T10:00:34", "speed": 2.0, "state": "Landing", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 8.0}},
        {"timestamp": "2024-03-18T10:00:35", "speed": 2.0, "state": "Landing", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 6.0}},
        {"timestamp": "2024-03-18T10:00:36", "speed": 2.0, "state": "Landing", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 4.0}},
        {"timestamp": "2024-03-18T10:00:37", "speed": 2.0, "state": "Landing", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 2.0}},
        {"timestamp": "2024-03-18T10:00:38", "speed": 2.0, "state": "Landing", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 0.0}},

        # Final idle (39-40s)
        {"timestamp": "2024-03-18T10:00:39", "speed": 0.0, "state": "Idle", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 0.0}},
        {"timestamp": "2024-03-18T10:00:40", "speed": 0.0, "state": "Idle", "status": "OK", 
         "position": {"x": 0.0, "y": 0.0, "z": 0.0}}
    ]
}

# Ensure the outputs directory exists
os.makedirs('/tmp/resim/outputs/', exist_ok=True)

# Set up logging
logging.basicConfig(
    filename='/tmp/resim/outputs/test.log',
    level=logging.INFO,
    format='%(message)s',  # We'll just log the raw JSON data
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    print("Hello from Build container!")
    
    # Write the entire flight_data structure as a single JSON file
    with open('/tmp/resim/outputs/test.log', 'w') as f:
        json.dump(flight_data, f, indent=2)
    
    print("Completed writing flight data. Exiting.")

if __name__ == "__main__":
    main() 
