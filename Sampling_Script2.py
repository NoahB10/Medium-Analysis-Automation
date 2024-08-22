import bluetooth
import threading
from core import connect
import time
import logging
from datetime import datetime

class Method:
    def __init__(self, ports, time):
        if not isinstance(ports, list):
            raise TypeError("\'ports\' must be of type list")
        self.ports = ports
        if not isinstance(time, int):
            raise TypeError("\'time\' must be of type int")
        if(time > 9999 or time < 0):
            raise ValueError("\'time\' must be between 0 and 9999")
        self.time = time
    def __str__(self):
        toReturn = f"{self.timeStringFormat()},"
        for port in self.ports:
            toReturn+=f'{str(port).zfill(2)},'
        return toReturn
    def timeStringFormat(self):
        return str(self.time).zfill(4)

class Sequence:
    def __init__(self, methods):
        if not isinstance(methods, list):
            raise TypeError("\'methods\' must be of type list")
        if len(methods)<1:
            raise ValueError("\'methods\' must be a list of length >= 1")
        self.methods = methods
    
    def __str__(self):
        toReturn = "@P,"
        for i in range(len(self.methods)):
            toReturn+=f'M{i+1},{str(self.methods[i])}'
        return toReturn+"\n\n"
    

class Pump:
    def __init__(self, pump_conn):
        """
        Initializes the Pump class with a connection to the pump.

        Args:
            pump_conn: An object representing the pump connection.
        """ 
        self.pump_conn = pump_conn
        pump_conn.openConnection()

    def send_settings(self, volume, rate, delay): 
        """
        Sends the specified volume, rate, and delay settings to the pump.

        Args:
            volume: The volume to be pumped.
            rate: The rate at which the pump should operate.
            delay: The delay before the pump starts.
        """
        self.pump_conn.setVolume(volume)   
        time.sleep(0.3)    
        self.pump_conn.setRate(rate) 
        time.sleep(0.3)        
        self.pump_conn.setDelay(delay) 
        time.sleep(0.3) 

    def timeread(self):
        """
        Returns the integer time that has elapsed in minutes.

        Returns:
            float: The elapsed time in minutes.
        """
        string = self.pump_conn.getElapsedTime()
        elapsed_time_str = string[1]  # Assuming the relevant time string is at index 1
        numbers = elapsed_time_str[15:22]  # Adjust slicing if the time runs past 10 minutes
        return float(numbers)
    
    def start_pump(self):
        """Starts the pump with the current settings."""
        self.pump_conn.startPump()

    def stop_pump(self):
        """Stops the pump."""
        self.pump_conn.stopPump()


class AmuzaConnection:
    
    isInProgress = False
    currentState = 0
    stateList = ["Resting", "Ejected Tray", "Unknown", "Unknown", "Moving Tray",
                 "Unknown", "Unknown", "Unknown", "Unknown", "Moving",
                 "Unknown", "Unknown", "Unknown", "Unknown", "Unknown",
                 "Unknown", "Unknown", "Unknown", "Unknown", "Unknown"]
    
    def queryThread(self, threadEvent, socket):
        while(threadEvent.is_set()):
            socket.send("@Q\n")
            logging.debug("Sent Query")
            time.sleep(1)
    
    def receptionThread(self, threadEvent, socket):
        currentCmd = ""
        while (threadEvent.is_set()):
            data = socket.recv(1024)  # Adjust buffer size as necessary
            decoded = data
            try:
                decoded = data.decode()
            except:
                logging.warning("Failed to Decrypt")
            logging.info(f"Received: {decoded}")  # Assuming data is UTF-8 encode
            currentCmd+=str(decoded)
            if(str(decoded).endswith("\n")):
               self.handleRecieved(currentCmd)
               currentCmd = ""
    
    def loopThread(self, threadEvent, sequence):
        while(threadEvent.is_set()):
            if(not self.checkProgress()):
                self.Move(sequence)
                #print(f"Moving To: {str(sequence)}")
                logging.info(f"Moving To: {str(sequence)}")
    
    def handleRecieved(self, cmd):

        logging.info(f"Handling: {cmd}")
        if(cmd[:2] == "@E"):
            logging.info(f"Exited with Exit Code {cmd[3]}")
        elif(cmd[:2] == "@q"):
            data = cmd[3:].split(',')
            #print(f"Status Update: {str(data)}")
            if(data[1]=='0'):
                self.setProgress(False)
            else:
                self.setProgress(True)
                print(f"Method number {data[1]}") 
                print(f"Time left at well {data[2][:len(data[2])-1].lstrip('0')+data[2][len(data[2])-1]}: {data[3][:len(data[3])-1].lstrip('0')+data[3][len(data[3])-1]} seconds") # this long line removes trailing zeroes while accounting for the edge case of "0"
            logging.info(f"Status Update: {cmd}")
            self.currentState = int(data[0])
            
        else:
            print(f"? {cmd}")
            
    
    def __init__(self, showOutputInConsole):
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
        
        currentTime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_handler = logging.FileHandler(f'logs/AMUZA-{currentTime}.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        
        for handler in logging.getLogger().handlers:
            logging.getLogger().removeHandler(handler)
        
        logging.getLogger().addHandler(file_handler)
        self.showOutput = showOutputInConsole
        print(f"AMUZA Interface Initiated - Detailed Logs can be found in AMUZA-{currentTime}.log")
        logging.info("AMUZA Interface Initiated")
    
    def well_mapping(self, locations):
        self.well_map = {}  # Initialize the dictionary
        rows = "ABCDEFGH"
        columns = range(1, 13)
        counter = 1
        
        # Generate the well_map dictionary
        for column in columns:
            for row in rows:
                well_location = f"{row}{column}"
                self.well_map[well_location] = counter
                counter += 1

        # Create a list of numeric values based on input locations
        result = []
        for location in locations:
            result.append(self.well_map.get(location, None))  # Return None if location is not found
        
        return result  # Return the list of values
        
    
    def consoleInterface(self):
        while True:
            command = input()
            logging.info(f"User Input: {command}")
            if(self.checkProgress() and command != ("STOP" or "EXIT" or "STATUS")):
                print("Machine is currently doing something, send STOP to make your command work")
            if(command=="EXIT"):
                logging.info(f"Exiting...")
                print("Exiting...")
                return
            if(command=="DEMO MOVE"):
                logging.info("Sent Move Command")
                print("Sent Move Command")
                method1 = Method([1,5,13,71],15)
                sequence = Sequence([method1])
                self.Move(sequence)
                
            if(command=="SAMPLING"):
                logging.info("Sent Sampling Command")
                print("Sent Sampling Command")
                # One way to write the methods are from well location names and time
                loc = ['A7','B7','C7','D7']
                loc_m = self.well_mapping(loc)
                time = [197,167,197,177]
                rate = [90,90,100,100]
                method = []
                for i in range(0, len(loc)):
                    print(loc[i])
                    print(loc_m[i])
                    method.append(Sequence([Method([loc_m[i]],time[i])]))
                    print(method[i])
                self.Control_Move(method,rate,time)
                
            if(command=="FULLPLATE"):
                time = []
                rate = []
                method = []
                for i in range(1, 97):
                    method.append(Sequence([Method([i],167)]))
                    rate.append(90)
                    time.append(157)
                self.Control_Move(method,rate,time)
                
            if(command[:4]=="TEMP"):
                logging.info(f"Adjusting Temp To {command[5:]}") # extra char to remove space
                self.AdjustTemp(float(command[5:]))
            if(command=="MOVE"):
                print("How long at each well? (Seconds)")
                length = input()
                wellList = []
                while(True):
                    print("Enter a comma-seperated list of wells you want to enter")
                    rec = input()
                    rec = rec.split(',')
                    for entry in rec:
                        if(entry.isdigit()):
                            num = int(entry)
                            if(num < 1 or num > 96):
                                print(f"Please only input a number from 1-96. You have inputted {num} in your list.")
                            else:
                                wellList.append(num)
                        else:
                            print(f"You have a non-integer ({entry}) in your list. Please only input numbers from 1-96.")
                            break
                    print(f"Final well list: {wellList}")
                    print("Confirm? Y/N")
                    confirm = input()
                    if(confirm=="Y"):
                        break
                    print("Redoing...")
                print("Do you want to loop this command? Y/N")
                loop = False
                while(True):
                    rec = input()
                    if(rec == "Y"):
                        loop = True
                        break
                    elif(rec == "N"):
                        break
                    else:
                        print("Invalid Input. Do you want to loop this command? Y/N")
                method = Method(wellList,int(length))
                sequence = Sequence([method])
                self.Move(sequence)
                print(f"Moving To: {str(sequence)}")
                logging.info(f"Moving To: {str(sequence)}")
                if(loop):
                    print("Type END to end the loop")
                    loopEvent = threading.Event()
                    loopEvent.set()
                    loopThread = threading.Thread(target = self.loopThread,args = (loopEvent, sequence))
                    loopThread.start()
                    while(True):
                        rec = input()
                        if(rec == "END"):
                            loopEvent.clear()
                            break
                        else:
                            print("Type END to end the loop")
            if(command=="STOP"):
                logging.info("Stopping...")
                self.Stop()
            if(command=="STATUS"):
                logging.info(f"Machine is currently: {self.stateList[self.currentState-1]} (ID: {self.currentState})") #-1 to adjust for the shift
                print(f"Machine is currently: {self.stateList[self.currentState-1]}  (ID: {self.currentState})")
            if(command=="CUSTOM"):
                print("What do you want to send?")
                cmd = input()
                print(f"Sending command \"{cmd}\"")
                logging.info(f"Sending Custom Command: {cmd}")
                self.socket.send(cmd)
            if(command=="EJECT"):
                logging.info("Ejecting...")
                self.Eject()
            if(command=="INSERT"):
                logging.info("Inserting...")
                self.Insert()
            if(command=="HELP"):
                print("EXIT - Exit the program\nDEMO MOVE - quick preprogrammed move command for debugging\nTEMP <float value between 0 and 99.9> - Adjust temperature\nMOVE - Wizard to move machine\nSTOP - Stop current action\nSTATUS - Get current status of the machine\nCUSTOM - Send custom command. Start it with @, end it with \\n\nEJECT - Eject the tray\nINSERT - Insert the tray\nHELP - Open this menu\nNEEDLE - Adjust the needle height")
            
            if(command=="NEEDLE"):
                print("UP to move needle up, DOWN to move needle down, FINISH to exit this wizard")
                self.socket.send("@N\n")
                while True:
                    cmd = input()
                    if(cmd=="UP"):
                        logging.info("Moving Needle Up")
                        self.NeedleUp()
                    elif(cmd=="DOWN"):
                        logging.info("Moving Needle Down")
                        self.NeedleDown()
                    elif(cmd=="FINISH"):
                        logging.info("Finished Needle Adjustments")
                        print("Finished Needle Adjustments")
                        self.socket.send("@V,180\n")
                        time.sleep(0.2)
                        self.socket.send("@T\n")
                        break
                    else:
                        print("Unknown Command - UP to move needle up, DOWN to move needle down, FINISH to exit this wizard")
    
    def NeedleUp(self):
        self.socket.send("@U01\n")
    
    def NeedleDown(self):
        self.socket.send("@D01\n")
        
    def Eject(self):
        self.socket.send("@Y\n")
    
    def Insert(self):
        self.socket.send("@Z\n")
    
    def Stop(self):
        self.socket.send("@T\n")
        pump.stop_pump()
    
    def Move(self, sequence):
        self.socket.send(str(sequence))

    def Control_Move(self,method,rate,duration):
        for i in range(0, len(duration)):
            #sequence = Sequence(method[i])
            #Clean by dipping into the vat at start
            pump.send_settings(-30000,120,0)
            pump.start_pump() if i == 0 else None
            time.sleep(90)
            self.Move(method[i])
            pump.send_settings(-30000,rate[i],0)
            time.sleep(duration[i]+10) # Use a minimum delay of 4.5s but likely will need longer
        pump.stop_pump()
 
    def AdjustTemp(self, temperature):
        if not isinstance(methods, float):
            raise TypeError("\'methods\' must be of type float")
        if(temperature < 0 or temperature > 99.9):
            raise ValueError("\'methods\' must be a list of length >= 1")
        self.socket.send(f"@V,{temperature}")
    
    def setProgress(self, val):
        self.isInProgress = val
    
    def checkProgress(self):
        return self.isInProgress
    
    def connect(self):
        print(f"Scanning")
        logging.info("Scanning")
        nearby_devices = bluetooth.discover_devices(lookup_names=True,lookup_class=True)
        print("Found {} devices.".format(len(nearby_devices)))
        logging.info("Found {} devices.".format(len(nearby_devices)))
        address = ""
        for addr, name, device_class in nearby_devices:
            print(f"  Address: {addr}")
            print(f"  Name: {name}")
            print(f"  Class: {device_class}")
            logging.info(f"  Address: {addr}")
            logging.info(f"  Name: {name}")
            logging.info(f"  Class: {device_class}")
            if(name=='FC90-0034'):
                address=addr
        if(address==""):
            print("AMUZA not found, press ENTER to exit")
            logging.critical("AMUZA not found, press ENTER to exit")
            input()
            exit()
        print("Attempting to Connect to AMUZA")
        logging.info("Attempting to Connect to AMUZA")
        socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        try:
            socket.connect((address,1))
        except:
            print("Connection Failure, Press ENTER to exit")
            logging.critical("Connection Failure, Press ENTER to exit")
            input()
            exit()
        print("Connection Success")
        logging.info("Connection Success")
        socket.send("@?\n")
        time.sleep(0.2)
        socket.send("@Q\n")
        time.sleep(0.2)
        socket.send("@Z\n")
        self.socket = socket
        
        threads = threading.Event()
        threads.set()
        _queryThread = threading.Thread(target=self.queryThread, args=(threads, self.socket))
        _queryThread.setDaemon(True)
        _queryThread.start()
        receptionThread = None
        if(self.showOutput):
            _receptionThread = threading.Thread(target=self.receptionThread, args=(threads, self.socket))
            _receptionThread.setDaemon(True)
            _receptionThread.start()
        
if __name__ == '__main__':
    baudrate=9600 # MUST set baudrate in pump "System Settings", and MUST match this rate:
    port = '/dev/ttyUSB0' #for linux and windows is 'COM15'
    # initiate Connection 
    PUMP_conn = connect.Connection(port= port,baudrate=baudrate, multipump=False)
    pump = Pump(PUMP_conn)
    # Setup parameters for pump 
    direction = -1   #Make positive for infuse and negative for withdrae
    units='μL/min'		 	# OPTIONS: 'mL/min','mL/hr','μL/min','μL/hr'
    
    syringe = 30 #pick which syringe by using its size 
    if syringe == 1:
        diameter = 4.78 # 1ml syringe has diameter of 4.78
    elif syringe == 10:
        diameter = 14.5 # 10ml syringe has diameter of 14.5
    elif syringe == 30:
        diameter = 21.69 # 30ml syringe diameter
    PUMP_conn.setUnits(units)
    PUMP_conn.setDiameter(diameter) 
    
    connection = AmuzaConnection(True)
    connection.connect()
    connection.consoleInterface()