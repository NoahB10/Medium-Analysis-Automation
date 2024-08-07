import pandas as pd
import numpy as np
import sys
import time
import getopt
from queue import Queue
from SIX_SERVER_READER_3 import PotentiostatReader

window =25 #global variable window which appears in dataprocess or

class SteadyState:
    def __init__(self, data):
        self.data = np.array(data)
        self.std_dev = np.std(self.data)
        if data.size > 0:
            self.mean = np.mean(self.data)
        else:
            self.mean = np.nan
        

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
        #Read all of the lines in the file and save to lines variable
        try:
            with open(self.file_path, 'r', newline='') as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"File not found: {self.file_path}")
            sys.exit(1)
        #split up the lines appropriately
        data = [line.strip().split('\t') for line in lines]
        #turn them into a dataframe
        df = pd.DataFrame(data)
        df = df.loc[:, :8] #Get rid of columns not in use
        new_header = df.iloc[1] #keep the first row as the header
        df = df[3:] #store data from 3 rows on
        df.columns = new_header
        self.df = df
        index = []
        for i in range(3, len(self.df) + 2):
            a = self.df.loc[i, 'counter']
            if not a.isdigit():
                index.append(i)
        df2 = df.loc[0:index[0] - 1, :]
        df2 = df2.apply(pd.to_numeric)
        #Now that we have it all processed into df2, we want to calibrate them 
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
            if self.buffer > window:
                self.analyze_buffer(index)
                self.buffer = 0
    def organize_data(self,data):
        self.buffer = 0
        data = pd.DataFrame({
                            '#1ch1': [data[0]],
                            '#1ch2': [data[1]],
                            '#1ch3': [data[2]],
                            '#1ch4': [data[3]],
                            '#1ch5': [data[4]],
                            '#1ch6': [data[5]]})
        return data

    def analyze_buffer(self, index):
        for column in self.results.columns:
            """
            #Use this to skil any columns
            if column == 'Glutamate':
                continue
            """ 
            steady_state = SteadyState(self.results.loc[index - self.buffer + 1:index, column])
            i = self.results.columns.get_loc(column)
            ss_index = steady_state.test()
            if ss_index:
                value = int(abs(self.results.loc[index, column]) * 1000) / 1000
                if not self.outputs[i] or (not (self.outputs[i][-1] * self.thresh[i][0] <= value <= self.outputs[i][-1] * self.thresh[i][1])
                                          and (index - self.indices[i][-1] >= 200)):
                    self.outputs[i].append(value)
                    self.indices[i].append(index)
        #self.check_change(index)

    def check_change(self, index):
        for column in self.results.columns:
            """
            #Use this to skil any columns
            if column == 'Glutamate':
                continue
            """
            i = self.results.columns.get_loc(column)
            if len(self.outputs[i]) >= 2:
                self.sign[i] = 1 if self.outputs[i][-2] > self.outputs[i][-1] else 0
        if self.sign[0] is not None and all(x == self.sign[0] for x in self.sign[:]):
            new_row = pd.DataFrame([{
                'Glutamate': self.outputs[1][-1],
                'Glutamine': self.outputs[2][-1],
                'Glucose': self.outputs[3][-1],
                'Lactate': self.outputs[4][-1]
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

def main(file_path,live):
    processor = DataProcessor()
    #Get the data either from live or from a file 
    if live:
        DataLogger = PotentiostatReader(com_port=COM_PORT, baud_rate=BAUD, timeout=TIMEOUT, output_filename=file_path)
        index = 1
        DataLogger.line_one()
        while (1):
            list = DataLogger.run()
            data = [float(i) for i in list]
            print(data)
            if data:
                data = processor.organize_data(data)
                processor.calibrate_data(data)
                print("1")
                processor.analyze_buffer(index)
                index += 1
            time.sleep(1.7)  # Control the data acquisition rate
    else:
        processor.load_data(file_path)
        processor.create_buffer()
        #print(processor.output)
    debug_info = processor.get_debug_info()
    # Print or save the debug_info DataFrame as needed
    # print(debug_info)

if __name__ == "__main__":
    path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\Equipment\\JOBST\\"
    filename = 'Trial.txt'
    file_path = path + filename
    live = True # Flag to decide if read from the file (False) or write to it live (True)
    COM_PORT = "COM20"
    BAUD = 9600
    TIMEOUT = 0.5
    main(file_path,live)
#Latest update got the values input directly from the sensor working just need to make them save now.
#also the read file should be working more normal now as well
