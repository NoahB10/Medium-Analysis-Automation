import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# Define the path to the file
path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\Equipment\\JOBST\\"
filename = "Medium_Calibration_Test.txt"
file_path = path + filename

# Open the file in read mode and read the contents
with open(file_path, "r", newline="") as file:
    lines = file.readlines()

# Process the data
data = [line.strip().split("\t") for line in lines]
df = pd.DataFrame(data)
df = df.loc[:, :8]  # Select relevant columns for one sensor
new_header = df.iloc[1]  # Select the third row as header
df = df[3:]  # Take the data less the new header row
df.columns = new_header  # Set the new header

# Separate the data from comments and other information at the bottom
index = []
for i in range(3, len(df) + 2):
    a = df.loc[i, "counter"]
    if not a.isdigit():
        index.append(i)
        break  # Stop once the first non-digit is found

df2 = df.loc[0 : index[0] - 1, :]
df2 = df2.apply(pd.to_numeric)

# Subtract signals from blanks according to the rules
glutamate = df2["#1ch1"] - df2["#1ch2"]
glutamine = df2["#1ch3"] - df2["#1ch1"]
glucose = df2["#1ch5"] - df2["#1ch4"]
lactate = df2["#1ch6"] - df2["#1ch4"]

# Gain values
gain = pd.DataFrame(
    {
        "Glutamate": [0.97],
        "Glutamine": [0.418],
        "Glucose": [0.6854],
        "Lactate": [0.0609],
    }
)

# Apply gain values to results
results = pd.DataFrame(
    {
        "Glutamate": glutamate * gain.loc[0, "Glutamate"],
        "Glutamine": glutamine * gain.loc[0, "Glutamine"],
        "Glucose": glucose * gain.loc[0, "Glucose"],
        "Lactate": lactate * gain.loc[0, "Lactate"],
    }
)

# Plot the data
plt.figure(figsize=(14, 7))
for column in results.columns:
    plt.plot(df2["t[min]"], results[column], label=column)

plt.xlabel("Time (minutes)")
plt.ylabel("mA")
plt.title("Time Series Data for Selected Channels")
plt.legend()
plt.grid(True)
plt.gca().xaxis.set_major_locator(MaxNLocator(nbins=12))
plt.gca().yaxis.set_major_locator(MaxNLocator(nbins=12))
plt.show()
