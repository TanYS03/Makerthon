import serial
import time
import sys
import msvcrt  # Use msvcrt for non-blocking input on Windows
from pymongo import MongoClient
import pandas as pd
import datetime

# Database setup and connection
client = MongoClient("mongodb+srv://easontan7285:nb2XBcriGVzT2QhF@cluster0.u7gxoah.mongodb.net/?tls=true")
db = client["smartbin"]

# Collections
dustbin_col = db["dustbins"]
notification_col = db["notification"]

dustbin_df = pd.DataFrame(list(dustbin_col.find()))
notification_df = pd.DataFrame(list(notification_col.find()))

# Set up the serial port (adjust port as needed)
arduino = serial.Serial(port='COM6', baudrate=9600, timeout=2)

def read_serial():
    """Function to read data from Arduino."""
    if arduino.in_waiting:
        # Decode data while ignoring invalid characters
        return arduino.readline().decode(errors='ignore').strip()
    return None

def process_status_message(status_text):
    """Process Arduino status message like 'Empty', 'Half-full', or 'Low'."""
    dustbin_hard = "BIN010" 
    valid_statuses = ["Empty", "Half-full", "Low", "Full"]
    if status_text in valid_statuses:
        existing_dustbin = dustbin_col.find_one({"dustbin_id": dustbin_hard})

        if existing_dustbin:
            # Update the status in the dustbin collection
            dustbin_col.update_one(
                {"dustbin_id": dustbin_hard},
                {"$set": {"status": status_text}},
                upsert=True
            )
        else:
            # Insert a new document if it doesn't exist
            dustbin_col.insert_one({
                "dustbin_id": dustbin_hard,
                "status": status_text,
                "location": "Block A",
                "timestamp": datetime.datetime.now(),
                "type": "recycle"
            })

        existing_notification = notification_col.find_one({
            "dustbin_id": dustbin_hard,
            "isCollected": True
        })

        existing_notification2 = notification_col.find_one({
            "dustbin_id": dustbin_hard,
            "isCollected": False
        })

        if status_text == "Full":
            if existing_notification:
                notification_col.update_one(
                    {"dustbin_id": dustbin_hard},
                    {"$set": {
                        "timestamp": datetime.datetime.now(),
                        "notification_type": "signal",
                        "isCollected": False
                    }}
                )
            else:
                notification_col.insert_one({
                    "dustbin_id": dustbin_hard,
                    "location": "Block A",
                    "timestamp": datetime.datetime.now(),
                    "notification_type": "signal",
                    "isCollected": False
                })
        else:
            if existing_notification2:
                notification_col.update_one(
                    {"dustbin_id": dustbin_hard},
                    {"$set": {
                        "timestamp": datetime.datetime.now(),
                        "notification_type": "signal",
                        "isCollected": True
                    }}
                )
            else:
                notification_col.insert_one({
                    "dustbin_id": dustbin_hard,
                    "location": "Block A",
                    "timestamp": datetime.datetime.now(),
                    "notification_type": "signal",
                    "isCollected": True
                })
            
print("Connected. Press Enter to calibrate, or 'q' to quit.")

try:
    while True:
        # Non-blocking input: Check if there’s any serial data
        data = read_serial()
        
        # If there's data, print it to the console
        if data:
            print(data)
            process_status_message(data) 
        
        # Check if Enter was pressed using msvcrt for non-blocking input
        if msvcrt.kbhit():  # Checks if a key is pressed
            user_input = msvcrt.getch().decode()  # Get the keypress (as byte, then decode)
            
            if user_input.lower() == 'q':  # Exit loop if 'q' is pressed
                break
            elif user_input == '\r':  # If Enter is pressed, calibrate
                arduino.write(b'\n')  # Send Enter to Arduino (trigger calibration)
                print("Calibrating...")

        # Sleep to keep frequency of data reading consistent
        time.sleep(0.1)  # Adjust the delay based on Arduino's frequency

except KeyboardInterrupt:
    pass  # Handle KeyboardInterrupt exception
finally:
    arduino.close()  # Close the serial port
