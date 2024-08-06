import pandas as pd
import numpy as np

class SteadyState:
    def __init__(self, data):
        self.data = np.array(data)
        self.mean = np.mean(self.data)
        self.std_dev = np.std(self.data)

    def test(self):
        if abs(self.std_dev) < .006:# Dont go much lower then this as it will not work
            return 1
        else:
            return None

# Define the path to the file
path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\Equipment\\JOBST\\"
filename = 'Air_to_Standard_to_Buffer.txt'
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
df2 = df2.applymap(pd.to_numeric)

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

# Prepare to find steady state values
glutamate_o = []
glutamine_o = []
glucose_o = []
lactate_o = []
index_lactate_o = []
index_glutamate_o = []
index_glucose_o = []
index_glutamine_o = []

buffer = 0

for index, row in results.iterrows():
    buffer += 1
    if buffer > 10:
        for column in results.columns:
            steady_state = SteadyState(results.loc[index - buffer + 1:index, column])
            ss_index = steady_state.test()
            if ss_index:
                value = abs(results.loc[index, column])
                if column == "Glutamine" and (not glutamine_o or not(glutamine_o[-1] * 0.02 <= value <= glutamine_o[-1] * 20)):
                    glutamine_o.append(value)
                    index_glutamine_o.append(index)
                elif column == "Glucose" and (not glucose_o or not (glucose_o[-1] * 0.2 <= value <= glucose_o[-1] * 1.4)):
                    glucose_o.append(value)
                    index_glucose_o.append(index)
                elif column == "Lactate" and (not lactate_o or not (lactate_o[-1] * 0.2 <= value <= lactate_o[-1] * 1.4)):
                    lactate_o.append(value)
                    index_lactate_o.append(index)
                elif column == "Glutamate" and (not glutamate_o or not (glutamate_o[-1] * 0.9 <= value <= glutamate_o[-1] * 1.1)):
                    glutamate_o.append(value)
                    index_glutamate_o.append(index)
        buffer = 0
    #Now I have a script which can grab the steady states between max's and mins and need to determine when to stop and go on to next measurement    

# Create the output DataFrame
output = pd.DataFrame({
     #'Glutamate': pd.Series(glutamate_o),
    'Glutamine': pd.Series(glutamine_o),
    'Index1': pd.Series(index_glutamine_o),
    'Glucose': pd.Series(glucose_o),
    'Index2': pd.Series(index_glucose_o),
    'Lactate': pd.Series(lactate_o),
    'Index3': pd.Series(index_lactate_o),
})
print(max(output['Lactate']))
print(max(output['Index1']))
print(max(output['Glucose']))
print(max(output['Index2']))
print(max(output['Glutamine']))
print(max(output['Index3']))
print(max(output['Glucose']))
print(max(output['Glutamine']))
print(output)