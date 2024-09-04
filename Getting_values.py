from SIX_SERVER_READER_2 import PotentiostatReader


path = "C:\\Users\\NoahB\\Documents\\HebrewU Bioengineering\\Local_Project_Code\\"
filename = 'Trial.txt'
file_path = path + filename
COM_PORT = "COM20"
BAUD = 9600
TIMEOUT = 0.5
DataLogger = PotentiostatReader(com_port=COM_PORT, baud_rate=9600, timeout=TIMEOUT, output_filename=file_path)
while(1):
    list = DataLogger.run()
    print(list)
