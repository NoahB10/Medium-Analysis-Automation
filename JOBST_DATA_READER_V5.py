import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import  MaxNLocator
from scipy.signal import find_peaks

class SteadyState:
    def __init__(self, data):
        """
        Initialize the SteadyState with a column of data.
        
        Parameters:
        data (list or array-like): The input column of data.
        """
        self.data = np.array(data)
        self.mean = np.mean(self.data)
        self.std_dev = np.std(self.data)

    def test(self):
        """
        Determine the index at which the steady state is reached.
        
        Returns:
        int: The index at which the steady state condition is met, otherwise None.
        """
        if abs(self.std_dev) < 3:
            return 1
        else:
            return None
        
# Define the path to the file
path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\\Equipment\\JOBST\\"
filename = 'W1237O_Test_22.7.24_2.txt'
file_path = path + filename
# Open the file in read mode
with open(file_path, 'r', newline='') as file:
    # Read the contents of the file
    lines =  file.readlines() 
data = [line.strip().split('\t') for line in lines]
df = pd.DataFrame(data)
df = df.loc[:,:8]#8 is used because it is only one sensor, if there are more then will be more relevant columns
new_header = df.iloc[1]  # Select the third row
df = df[3:]  # Take the data less the new header row
df.columns = new_header  # Set the new header
#print(df)
#print(df['#1ch1'])



#Now want to seperate the data from the comments and other information at the bottom
index = []
for i in range(3,len(df)+2): # not sure why i can add 2 more but it works 
    a = df.loc[i,'counter']
    # print(a)
    if not a.isdigit():
        #remove from the data set and make new matrix 
        index.append(i)
df2 = df.loc[0:index[0]-1,:]
df2 = df2.applymap(pd.to_numeric) 


# Subtract signals from blanks according to the 
glutamate = df2['#1ch1'] - df2['#1ch2']
glutamine = df2['#1ch3'] - df2['#1ch1'] # play around with subtracting #1ch1 or the glutamate channel (JOBST says subtract channel 1)
glucose = df2['#1ch5'] - df2['#1ch4']
lactate = df2['#1ch6'] - df2['#1ch4']
gain = pd.DataFrame({'Glutamate': [0.97] ,'Glutamine': [0.418], 'Glucose': [0.6854],'Lactate': [0.0609]})
results = pd.DataFrame({
    'Glutamate': glutamate * gain.loc[0, 'Glutamate'],
    'Glutamine': glutamine * gain.loc[0, 'Glutamine'],
    'Glucose': glucose * gain.loc[0, 'Glucose'],
    'Lactate': lactate * gain.loc[0, 'Lactate']
})
#Find the stop index for when the graph reaches steady state
#When parsing through live feed will need to check each one and see if they reach S.S and only stop after they all reach S.S
data = pd.DataFrame({'Glutamate': [],'Glutamine': [], 'Glucose': [],'Lactate': []})
readings = pd.DataFrame({'Glutamate': [],'Glutamine': [], 'Glucose': [],'Lactate': []})
# output = pd.DataFrame({'Glutamate': [],'Glutamine': [], 'Glucose': [],'Lactate': []})
# output = pd.DataFrame({'Glutamate': [],'Glutamine': [], 'Glucose': [],'Lactate': [], 'index1': [],'index2': [],'index3': [],'index4': []})
baseline = []
baseline_loc = []
ss = []
ss_loc = []
glucose_o = []
glutamine_o = []
lactate_o = []
glutamate_o = []
index1 = []
index2 = []
index3 = []
index4 =[]
row_count = 0
#python cant copy lists without referring to the same storage locations
for column in data.columns:
    baseline.append(None)
    baseline_loc.append(None)
    ss.append(None)
    ss_loc.append(None)
buffer=0
row_count = 0
Change = False
for index, row in results.iterrows(): #modify this when I get the live feed, right now this is for saved results (note index is the row number and row is the row content)
    data.loc[index] = row
    buffer = buffer+1
    if buffer > 12: #Need to optomize the paramter
        for column in data.columns:
            i = data.columns.get_loc(column)
            steady_state = SteadyState(data.loc[index-buffer:,column])
            ss_index = steady_state.test() #currently a flag for if it reaches SS
            if ss_index:
                value = data.loc[index,column]#offset by 3
                 #check that the value is not close to the previous value meaning its a on the same peak.
                if column == "Glutamine" and (not glutamine_o or (len(glutamine_o) and glutamine_o[-1]*0.4 <= value <= glutamine_o[-1]*1.6)):
                    glutamine_o.append(value)
                    index1.append(index)
                elif column == "Glucose" and (not glucose_o or (len(glucose_o) and glucose_o[-1]*0.8 <= value <= glucose_o[-1]*1.2)):
                    glucose_o.append(value)
                    index2.append(index)
                elif column == "Lactate" and (not lactate_o or (len(lactate_o) and lactate_o[-1]*0.55 <= value <= lactate_o[-1]*1.35)): 
                    lactate_o.append(value)
                    index3.append(index)
                elif column == "Glutamate" and (not glutamate_o or (len(glutamate_o) and glutamate_o[-1]*0.9 <= value <= glutamate_o[-1]*1.1 )):
                    glutamate_o.append(value)
                    index4.append(index)
        buffer = 0

output = {'Glutamate': [],'Glutamine': glutamine_o, 'Glucose': glucose_o,'Lactate': lactate_o, 'index1': [],'index2': [],'index3': [],'index4': []}
output = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in output.items()]))
print(output)
#have a very big problem that the program doesnt work if there is no change detected. Add another condition to save the reading and continue anyways 
#should just go through the values and keep updating each one on their own and not group them together. dont need to discard many values then 

"""
         if detect_rapid_change(data,column) and not Change and not all(x is not None for x in baseline):
            # Average the previous values as the baseline for the specific column
            if not baseline[i]:
                baseline[i]= data.loc[:index,column].mean()
                baseline_loc[i] =index #saves which row the change occured at (index) in the correct column
                Change = all(x is not None for x in baseline) # check if they are all changed now
            else: # case where we keep seeing there is a spike in a channel we know has spiked already 
                continue
        elif Change:
        elif all(x is not None for x in baseline) and Change:
            if detect_steady_state(data.loc[max(baseline_loc):, column]) is not None: #Now we know there is some sort of growth and want to find when each channel reaches S.S
                start_index = max(baseline_loc) # jump ahead to where the last spike was
                if  not ss[i]:
                    ss_loc[i] = detect_steady_state(data.loc[start_index:, column]) + start_index #offset to keep track of actual value
                    ss[i] = data.loc[ss_loc[i],column]
                    if all(x is not None for x in ss):
                        readings = pd.concat([readings, pd.DataFrame([ss], columns=data.columns)], ignore_index=True)
                        Change = False
                        for column in data.columns:
                            ss[data.columns.get_loc(column)] = None
                            ss_loc[data.columns.get_loc(column)] = None
                else: # case where we keep seeing there is a spike in a channel we know has spiked already 
                    continue
        #third case is then there is a rapid change in another direction
        #elif detect_rapid_change(data,column) and not Change:
"""