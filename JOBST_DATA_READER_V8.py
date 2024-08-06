import pandas as pd
import numpy as np
import sys
import threading
import time
import getopt
from queue import Queue
from SIX_SERVER_READER import com_port

window =25 #global variable window which appears in dataprocess or

class SteadyState:
    def __init__(self, data):
        self.data = np.array(data)
        self.mean = np.mean(self.data)
        self.std_dev = np.std(self.data)

    def test(self):
        if abs(self.std_dev) < 0.006:  # Don't go much lower than this as it will not work
            return 1
        else:
            return None

class DataProcessor:
    def __init__(self):
        self.df = None
        self.results = None
        self.output = pd.DataFrame(columns=['Glutamate', 'Glutamine', 'Glucose', 'Lactate'])
        self.buffer = 0
        self.outputs = [[] for _ in range(4)]
        self.indices = [[] for _ in range(4)]
        self.thresh = [[0.2, 100], [0.2, 50], [0.2, 100], [0.2, 100]] # list for glutamate, glutamine, glucose, lactate
        self.sign = [None] * 4

    def load_data(self,file_path):
        self.file_path = file_path
        try:
            with open(self.file_path, 'r', newline='') as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"File not found: {self.file_path}")
            sys.exit(1)

        data = [line.strip().split('\t') for line in lines]
        df = pd.DataFrame(data)
        df = df.loc[:, :8]
        new_header = df.iloc[1]
        df = df[3:]
        df.columns = new_header
        self.df = df

    def process_data(self):
        index = []
        for i in range(3, len(self.df) + 2):
            a = self.df.loc[i, 'counter']
            if not a.isdigit():
                index.append(i)
        df2 = self.df.loc[0:index[0] - 1, :]
        df2 = df2.apply(pd.to_numeric)
        self.calibrate_data(df2)

    def calibrate_data(self, df2):
        # Subtract signals from blanks
        glutamate = df2['#1ch1'] - df2['#1ch2']
        glutamine = df2['#1ch3'] - df2['#1ch1']
        glucose = df2['#1ch5'] - df2['#1ch4']
        lactate = df2['#1ch6'] - df2['#1ch4']
        gain = pd.DataFrame({'Glutamate': [0.97], 'Glutamine': [0.418], 'Glucose': [0.6854], 'Lactate': [0.0609]})
        self.results = pd.DataFrame({
            'Glutamate': glutamate * gain.loc[0, 'Glutamate'],
            'Glutamine': glutamine * gain.loc[0, 'Glutamine'],
            'Glucose': glucose * gain.loc[0, 'Glucose'],
            'Lactate': lactate * gain.loc[0, 'Lactate']
        })

    def create_buffer(self):
        for index, row in self.results.iterrows():
            self.buffer += 1
            if self.buffer >window:
                self.analyze_buffer(index)
                self.buffer = 0

    def analyze_buffer(self, index):
        for column in self.results.columns:
            if column == 'Glutamate':
                continue
            steady_state = SteadyState(self.results.loc[index - self.buffer + 1:index, column])
            i = self.results.columns.get_loc(column)
            ss_index = steady_state.test()
            if ss_index:
                value = int(abs(self.results.loc[index, column]) * 1000) / 1000
                if not self.outputs[i] or (not (self.outputs[i][-1] * self.thresh[i][0] <= value <= self.outputs[i][-1] * self.thresh[i][1])
                                          and (index - self.indices[i][-1] >= 200)):
                    self.outputs[i].append(value)
                    self.indices[i].append(index)
        self.check_steady_states(index)

    def check_steady_states(self, index):
        for column in self.results.columns:
            if column == 'Glutamate':
                continue
            i = self.results.columns.get_loc(column)
            if len(self.outputs[i]) >= 2:
                self.sign[i] = 1 if self.outputs[i][-2] > self.outputs[i][-1] else 0
        if self.sign[1] is not None and all(x == self.sign[1] for x in self.sign[1:]):
            new_row = pd.DataFrame([{
                'Glutamine': self.outputs[1][-1],
                'Glucose': self.outputs[2][-1],
                'Lactate': self.outputs[3][-1]
            }])
            if not new_row.dropna(axis=1).empty and (self.output.empty or not (new_row.iloc[0] == self.output.iloc[-1]).all()):
                self.output = pd.concat([self.output, new_row], ignore_index=True)
            self.sign = [None] * 4

    def get_debug_info(self):
        return pd.DataFrame({
            'Glutamate': pd.Series(self.outputs[0]),
            'Index1': pd.Series(self.indices[0]),
            'Glutamine': pd.Series(self.outputs[1]),
            'Index2': pd.Series(self.indices[1]),
            'Glucose': pd.Series(self.outputs[2]),
            'Index3': pd.Series(self.indices[2]),
            'Lactate': pd.Series(self.outputs[3]),
            'Index4': pd.Series(self.indices[3]),
        })

class SerialPortReader(threading.Thread):
    def __init__(self, com_port, baud, timeout, serial_queues, lock):
        threading.Thread.__init__(self)
        self.com_port = com_port
        self.baud = baud
        self.timeout = timeout
        self.serial_queues = serial_queues
        self.lock = lock
        self.running = True

    def run(self):
        while self.running:
            with self.lock:
                for queue in self.serial_queues:
                    # Simulating reading data from the serial port
                    data = [str(time.time())] * 7
                    queue.put(data)
            time.sleep(self.timeout)

    def stop(self):
        self.running = False

class DataLogger:
    def __init__(self, com_port, poll_time, filename):
        self.poll_time = poll_time
        self.filename = filename
        self.lock = threading.Lock()
        self.serial_queues = []
        self.serial_reader = SerialPortReader(com_port, 9600, 1, self.serial_queues, self.lock)
        self.queue = Queue()
        self.serial_queues.append(self.queue)
        self.start_timestamp = round(time.time(), 4)
        self.last_timestamp = self.start_timestamp

    def start(self):
        print("### Starting.")
        self.serial_reader.start()
        self.log_data()

    def log_data(self):
        first_line = "Time/s\tCh1/nA\tCh2/nA\tCh3/nA\tCh4/nA\tCh5/nA\tCh6/nA\tT/°C"
        print(first_line)
        with open(self.filename, 'w') as file:
            file.write(first_line + '\n')
        read_data = True
        try:
            while read_data:
                time.sleep(0.001)  # sleep for 1 ms
                timestamp = round(time.time(), 4)
                delta_time = timestamp - self.last_timestamp
                if delta_time >= self.poll_time and not self.queue.empty():
                    data = []
                    while not self.queue.empty():  # fetching data
                        data.append(self.queue.get())
                    avg_data = [0] * 7  # 6 currents + temperature
                    for data_point in data:
                        for i in range(7):
                            avg_data[i] += float(data_point[i])
                    avg_data = [x / len(data) for x in avg_data]
                    avg_data.insert(0, timestamp - self.start_timestamp)
                    self.last_timestamp = timestamp
                    to_print = ("{:.2f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}"
                                "\t{:.3f}\t{:.3f}\t{:.3f}").format(*avg_data)
                    print(to_print)
                    if self.filename:
                        with open(self.filename, 'a') as file:
                            file.write(to_print + '\n')

        except KeyboardInterrupt:
            self.serial_reader.stop()

class CommandLineInterface:
    def __init__(self):
        self.com_port = None
        self.poll_time = 1
        self.filename = None

    def usage(self):
        print('Usage:')
        print(sys.argv[0] + ' -c <COM port> -p <poll_time> [-f <out_file>]')
        print("Available options:")
        print("-h --help: this text")
        print("-c --com: com port to use. Example COM8")
        print("-p --poll: polling time in seconds")
        print("-f --file: output file where data is stored")
        print("Examples:")
        print("_______________________________")
        print("py_six_server.py -c COM6 -p 2.5")
        print("py_six_server.py -c COM6 -p 2.5 -f out.txt")
        print("py_six_server.py -c /dev/ttyUSB0 -p 2.5 -f out.txt")

    def parse_args(self, argv):
        try:
            opts, args = getopt.getopt(argv, "hc:p:f:", ["help", "com=", "poll=", "file="])
        except getopt.GetoptError as err:
            print(err)
            self.usage()
            sys.exit(2)

        for o, a in opts:
            if o in ("-h", "--help"):
                self.usage()
                sys.exit()
            elif o in ("-c", "--com"):
                self.com_port = a
            elif o in ("-p", "--poll"):
                self.poll_time = float(a)
            elif o in ("-f", "--file"):
                self.filename = a
            else:
                assert False, "unhandled option"

        if not self.com_port:
            print("Missing COM port parameter")
            self.usage()
            sys.exit(2)

def main(file_path,live):
    processor = DataProcessor(file_path)
    #Get the data either from live or from a file 
    if live:
        DataLogger(com_port, 1, file_path)
    else:
        processor.load_data(file_path)
    processor.process_data()
    processor.create_buffer()
    print(processor.output)
    debug_info = processor.get_debug_info()
    # Print or save the debug_info DataFrame as needed
    # print(debug_info)

if __name__ == "__main__":
    path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\Equipment\\JOBST\\"
    filename = 'W1237O_Test_22.7.24_2.txt'
    file_path = path + filename
    live = True # Flag to decide if read from the file (False) or write to it live (True)
    COM_PORT = "COM20"
    BAUD = 9600
    TIMEOUT = 0.5
    main(file_path,live)
