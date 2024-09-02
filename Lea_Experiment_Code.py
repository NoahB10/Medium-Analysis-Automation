import threading
import time
from SIX_SERVER_READER import PotentiostatReader
import AMUZA_Master

# Connect to the AMUZA
connection = AMUZA_Master.AmuzaConnection(True)
connection.connect()

# Set global sparcing variables for time
t_buffer = 75
t_sampling = 95  # used to be 110 but 95 seems to be pretty accurate for 180 microL

# Define the control sequence definition
def Control_Move(method, duration):
    for i in range(0, len(duration)):
        time.sleep(t_buffer)
        connection.Move(method[i])
        delay = 1
        """
        Loc = str(method[i])
        Loc = int(Loc[-1])
        if Loc > 80:
            delay = 3
        elif Loc > 55:
            delay = 2
        elif Loc > 30:
            delay = 1 
        """
        time.sleep(duration[i] + 9 + delay)  # Use a minimum delay of 4.5s but likely will need longer

# Function to run the AMUZA control sequence
def run_command(command):
    if command == "HALFPLATE":
        connection.AdjustTemp(5)  # Chill the plate temp to keep medium from changing
        method = []
        duration = [t_sampling] * 47
        for i in range(1, 48):
            method.append(AMUZA_Master.Sequence([AMUZA_Master.Method([i], t_sampling)]))
        Control_Move(method, duration)

    elif command == "FULLPLATE":
        connection.AdjustTemp(5)  # Chill the plate temp to keep medium from changing
        method = []
        duration = [t_sampling] * 95
        for i in range(1, 96):
            method.append(AMUZA_Master.Sequence([AMUZA_Master.Method([i], t_sampling)]))
        Control_Move(method, duration)

    elif command == "LEAPLATE":
        connection.AdjustTemp(5)  # Chill the plate temp to keep medium from changing
        method = []
        locations = connection.generate_sequence()
        duration = [t_sampling] * 95
        for i in range(0, 95):
            loc = locations[i]
            method.append(AMUZA_Master.Sequence([AMUZA_Master.Method([loc], t_sampling)]))
        Control_Move(method, duration)

# Function to run the DataLogger
def run_datalogger():
    path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\Local_Project_Code\\"
    filename = input("Please input a Filename:")
    filename = filename + '.txt'
    file_path = path + filename
    COM_PORT = "COM20"
    BAUD = 9600
    TIMEOUT = 0.5
    DataLogger = PotentiostatReader(com_port=COM_PORT, baud_rate=9600, timeout=TIMEOUT, output_filename=file_path)
    DataLogger.line_one()

    while True:
        data_list = DataLogger.run()

# Start the DataLogger in a separate thread
datalogger_thread = threading.Thread(target=run_datalogger)
datalogger_thread.start()

# Get the command input and run the corresponding control sequence
command = input("Please type a mode: HALFPLATE, FULLPLATE, LEAPLATE:")
run_command(command)

# Ensure that the main thread waits for the DataLogger thread to finish if needed
#datalogger_thread.join()