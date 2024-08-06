import pandas as pd
import numpy as np

ss_thresh = 1 # .006 for the other file

class SteadyState:
    def __init__(self, data):
        self.data = np.array(data)
        self.mean = np.mean(self.data)
        self.std_dev = np.std(self.data)

    def test(self):
        if abs(self.std_dev) < ss_thresh:# Dont go much lower then this as it will not work
            return 1
        else:
            return None

# Define the path to the file
path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\Equipment\\JOBST\\"
filename = 'Medium_Calibration_Test.txt'
file_path = path + filename

# Read the file and process the data
with open(file_path, 'r', newline='') as file:
    lines = file.readlines()
data = [line.strip().split('\t') for line in lines]
df = pd.DataFrame(data)
df = df.loc[:, :8]
new_header = df.iloc[1]
df = df[3:]
df.columns = new_header

# Separate the data from the comments and other information at the bottom
index = []
for i in range(3, len(df) + 2):
    a = df.loc[i, 'counter']
    if not a.isdigit():
        index.append(i)
df2 = df.loc[0:index[0] - 1, :]
df2 = df2.map(pd.to_numeric)

# Subtract signals from blanks
glutamate = df2['#1ch1'] - df2['#1ch2']
glutamine = df2['#1ch3'] - df2['#1ch1']
glucose = df2['#1ch5'] - df2['#1ch4']
lactate = df2['#1ch6'] - df2['#1ch4']
gain = pd.DataFrame({'Glutamate': [0.97], 'Glutamine': [0.418], 'Glucose': [0.6854], 'Lactate': [0.0609]})
results = pd.DataFrame({
    'Glutamate': glutamate * gain.loc[0, 'Glutamate'],
    'Glutamine': glutamine * gain.loc[0, 'Glutamine'],
    'Glucose': glucose * gain.loc[0, 'Glucose'],
    'Lactate': lactate * gain.loc[0, 'Lactate']
})
output = pd.DataFrame({
    #    'Glutamate': [],
    'Glutamine': [],
    'Glucose': [],
    'Lactate': []})

# Prepare to find steady state values
glutamate_o = []
glutamine_o = []
glucose_o = []
lactate_o = []
outputs = [glutamate_o,glutamine_o,glucose_o,lactate_o]
index_lactate_o = []
index_glutamate_o = []
index_glucose_o = []
index_glutamine_o = []
indicies = [index_glutamate_o,index_glutamine_o,index_glucose_o,index_lactate_o]
inc_val = [[],[],[],[]]
inc_val_index = [[],[],[],[]]
#Min and max bounds for the ss to be considered the same as the previous one 
thresh1 = [0.01,10] #glutamate
thresh2 = [0.01,10] #glutamine
thresh3 = [0.02,10] #glucose
thresh4 = [0.02,10] #lactate
thresh = [thresh1,thresh2,thresh3,thresh4]
sign = []
debug =1
for column in results.columns:
    sign.append(None)
"""
# Another simpler option if works can replace the definitions above
outputs = [[] for _ in range(4)]
indicies = [[] for _ in range(4)]
thresh = [[0.02, 20], [0.2, 1.4], [0.2, 1.4], [0.9, 1.1]]
"""
buffer = 0
for index, row in results.iterrows():
    buffer += 1
    if buffer > 25:
        #Determenening if there are any steady states reached in this window
        for column in results.columns:
            if column == 'Glutamate': 
                continue
            steady_state = SteadyState(results.loc[index - buffer + 1:index, column])
            i = results.columns.get_loc(column)
            ss_index = steady_state.test()
            if ss_index:
                value = int(abs(results.loc[index, column])*1000)/1000
                # Set 2 conditions, 
                # 1. The time between the two steps min 200 indicies or 3.4 [s]
                # 2. THe jump has to be significantly large enough to count 
                if not outputs[i] or (not (outputs[i][-1] * thresh[i][0] <= value <= outputs[i][-1] * thresh[i][1]) 
                                      and (index - indicies[i][-1] >= 300)):
                    outputs[i].append(value)
                    indicies[i].append(index)
                elif debug: #values which are excluded due to the thresholds 
                    inc_val[i].append(value)
                    inc_val_index[i].append(index)
        print(outputs)            
        #Now I have a script which can grab the steady states between max's and mins and need to determine when to stop and go on to next measurement    
        #Can check direction if it increased or decreased also can watch the indicies (this only works if i spike the test for certain because I need them all to increase or decrease)
        for column in results.columns:
            #Pick any columns to exclude if relevant
            if column == 'Glutamate': 
                continue
            i = results.columns.get_loc(column)
            if len(outputs[i]) >= 2:
                if outputs[i][-2] > outputs[i][-1]:
                    sign[i] = 1 
                else: 
                    sign[i] = 0 
                #print(sign)
                #print(outputs)
        if  sign[1] != None and all(x==sign[1] for x in sign[1:]): #here i set it to start at 1 to skip the first column 
            #go on to the next step now that we have all the same sign.
            #print(output[i][-1] for i in range(4))
            #print([lst[-1] for lst in outputs if lst])
            new_row = pd.DataFrame([{
                # 'Glutamate': outputs[0][-1],  # Assuming no corresponding last element for Glutamate
                'Glutamine': outputs[1][-1],
                'Glucose': outputs[2][-1],
                'Lactate': outputs[3][-1]
                }])
            if output.empty:
                output = pd.concat([output, new_row], ignore_index=True)
            else:
                temp = new_row == output.iloc[-1]
                if bool((temp == False).all().all()):
                    output = pd.concat([output, new_row], ignore_index=True)
            sign = [None for _ in sign]
        buffer = 0
print(output)
#once they all show the same sign then move on to the next

""" for column in results.columns:
        i = results.columns.get_loc(column)
        if outputs[i][-1]:
"""
# Create the output DataFrame
Debug_info = pd.DataFrame({
     #'Glutamate': pd.Series(glutamate_o),
    'Glutamate': pd.Series(glutamate_o),
    'Index1': pd.Series(index_glutamate_o),
    'Glutamine': pd.Series(glutamine_o),
    'Index2': pd.Series(index_glutamine_o),
    'Glucose': pd.Series(glucose_o),
    'Index3': pd.Series(index_glucose_o),
    'Lactate': pd.Series(lactate_o),
    'Index4': pd.Series(index_lactate_o),
})

"""
print(max(output['Lactate']))
print(max(output['Index1']))
print(max(output['Glucose']))
print(max(output['Index2']))
print(max(output['Glutamine']))
print(max(output['Index3']))
print(max(output['Glucose']))
print(max(output['Glutamine']))
"""
if debug:
    print(Debug_info)
