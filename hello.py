import time
import random
import logging
import os

# Ensure the logs directory exists
os.makedirs('/tmp/resim/inputs/logs', exist_ok=True)

# Set up logging
logging.basicConfig(
    filename='/tmp/resim/inputs/logs/test.log',
    level=logging.INFO,
    format='%(asctime)s,%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    print("Hello from Build container!")
    
    # Generate random time series data
    while True:
        value = random.uniform(0, 100)
        logging.info(f"{value}")
        time.sleep(1)

if __name__ == "__main__":
    main() 
