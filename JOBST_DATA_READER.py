import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import  MaxNLocator

def detect_steady_state(signal, window_size=15, threshold=0.005): #May want to change this to only compare thelast few values
    """
    Detect when a signal reaches a steady state.

    Parameters:
    signal (array-like): The signal data. 
    window_size (int): The size of the moving window.
    threshold (float): The standard deviation threshold to determine steady state.

    Returns:
    int: The index where the signal reaches a steady state. if there is none then None 
    """
    signal = pd.Series(signal)

    if len(signal) < window_size:
        return None
    
    moving_std = signal.rolling(window=window_size).std()
    
    steady_state_index = np.where(moving_std < threshold)[0]
    
    if len(steady_state_index) > 0:
        return steady_state_index[0]
    else:
        return None

def detect_rapid_change(df, column_name, threshold=.1):
    """
    Detects rapid changes in the last two points of a DataFrame column.

    Parameters:
    df (pd.DataFrame): The DataFrame containing the data.
    column_name (str): The name of the column to analyze.
    threshold (float): The threshold value to detect rapid change.

    Returns:
    bool: True if a rapid change is detected, False otherwise.
    """
    if len(df) < 2:
        # Not enough data points to detect a change
        return False
    
    # Calculate the derivative between the last two points
    derivative = df[column_name].iloc[-1] - df[column_name].iloc[-2] # actually just the difference in height but it is still relevant as the change in time is const. 

    # Check if the derivative surpasses the threshold
    return abs(derivative) > threshold

def detect_break_in_steady_state(signal, steady_state_index, window_size=10, change_threshold=0.01):
    """
    Detect when a signal breaks from steady state.

    Parameters:
    signal (array-like): The signal data.
    steady_state_index (int): The index where steady state starts.
    window_size (int): The size of the moving window.
    change_threshold (float): The threshold for detecting a significant change.

    Returns:
    int: The index where the signal breaks from steady state.
    """
    signal = pd.Series(signal)
    steady_state_signal = signal[steady_state_index:]
    
    moving_avg = steady_state_signal.rolling(window=window_size).mean()
    moving_diff = moving_avg.diff().abs()
    
    break_index = np.where(moving_diff > change_threshold)[0]
    
    if len(break_index) > 0:
        return steady_state_index + break_index[0]
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
    print(a)
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
results = pd.DataFrame({'Glutamate': glutamate,'Glutamine': glutamine, 'Glucose': glucose,'Lactate': lactate})

#Find the stop index for when the graph reaches steady state
#When parsing through live feed will need to check each one and see if they reach S.S and only stop after they all reach S.S
data = pd.DataFrame({'Glutamate': [],'Glutamine': [], 'Glucose': [],'Lactate': []})
readings = data
baseline = []
baseline_loc = []
ss = []
ss_loc = []
#python cant copy lists without referring to the same storage locations
for column in data.columns:
    baseline.append(None)
    baseline_loc.append(None)
    ss.append(None)
    ss_loc.append(None)

Change = False

for index, row in results.iterrows(): #modify this when I get the live feed, right now this is for saved results (note index is the row number and row is the row content)
    data.loc[index] = row
    for column in data.columns:
        i = data.columns.get_loc(column)
        #At the very begging detect when we spike to get started 
        if detect_rapid_change(data,column) and not Change and not all(x is not None for x in baseline):
            # Average the previous values as the baseline for the specific column
            if not baseline[i]:
                baseline[i]= data.loc[:index,column].mean()
                baseline_loc[i] =index #saves which row the change occured at (index) in the correct column
                Change = all(x is not None for x in baseline) # check if they are all changed now
            else: # case where we keep seeing there is a spike in a channel we know has spiked already 
                continue
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
        # elif detect_rapid_change(data,column) and not Change:

