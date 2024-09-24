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
    for i in range(0, len(method)):
        time.sleep(t_buffer)
        connection.Move(method[i])
        delay = 1
        time.sleep(duration[0] + 9 + delay)  # Use a minimum delay of 4.5s but likely will need longer

# Function to run the AMUZA control sequence
def run_command(command):
    method = []
    if command == "RUNPLATE":
        connection.AdjustTemp(5)  # Chill the plate temp to keep medium from changing
        size = input("Please insert comma seperated dimenstion of the plate (Rows,Columns) MAX(8,12): ")
        size = [int(dim) for dim in size.split(",")]
        if size[0] > 8 or size[1] > 12:
            print("Error: Maximum size allowed is 8 rows and 12 columns.")
        locations = []  # Initialize the dictionary
        rows = "ABCDEFGH"[:size[0]]  # Restrict to the number of rows as per input
        columns = range(1, size[1] + 1)  # Restrict columns as per input
        for row in rows:
            for column in columns:
                well_location = f"{row}{column}"
                locations.append(well_location)
        locations = connection.well_mapping(locations)
        print(locations)
        print(size[0]*size[1])
        for i in range(0, size[0]*size[1]):
            method.append(AMUZA_Master.Sequence([AMUZA_Master.Method([i], t_sampling)]))
        Control_Move(method, [t_sampling])
    
    elif command == "MOVE":
        connection.AdjustTemp(5)  # Chill the plate temp to keep medium from changing
        wells = input("Please insert comma seperated well sequence like A1,B2: ")
        well_list = wells.replace(" ", "").split(",")
        locations = connection.well_mapping(well_list)
        print(locations)
        for i in range(0, len(locations)):
            loc = locations[i]
            print(loc)
            method.append(AMUZA_Master.Sequence([AMUZA_Master.Method([loc], t_sampling)]))
        Control_Move(method, [t_sampling])
        
    elif command == "EJECT":
        connection.Eject()
        
    elif command == "INSERT":
        connection.Insert()

# Function to run the DataLogger
def run_datalogger(filename):
    path = r'/home/pi/Documents/Medium-Analysis-Automation/Data_Collected/'
    file_path = path + filename
    template_file_path = r'/home/pi/Documents/Medium-Analysis-Automation/example_format.txt'
    COM_PORT = '/dev/ttyUSB0'
    BAUD = 9600
    TIMEOUT = 0.5
    DataLogger = PotentiostatReader(com_port=COM_PORT, baud_rate=9600, timeout=TIMEOUT, output_filename=file_path)
    while True:
        data_list = DataLogger.run()

# Get the filename input
time.sleep(7)
filename = input("Please input a Filename:")
filename = filename + '.txt'

# Start the DataLogger in a separate thread, passing the filename
datalogger_thread = threading.Thread(target=run_datalogger, args=(filename,))
datalogger_thread.start()

# Loop for continuous command input
while True:
    command = input("Please type a mode: INSERT, EJECT, RUNPLATE, MOVE (type EXIT to stop):").upper()
    
    # Check if the user wants to exit
    if command == "EXIT":
        print("Exiting...")
        break
    
    # Run the corresponding command
    run_command(command)

# Optionally wait for the DataLogger thread to finish
#datalogger_thread.join()