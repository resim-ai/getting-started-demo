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
    
    for i in range(100):
        value = random.uniform(0, 100)
        logging.info(f"{value}")
        print(f"Generated value {i+1}/100: {value}")

    print("Completed generating 100 values. Exiting")

if __name__ == "__main__":
    main() 
