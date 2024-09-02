import serial
import time
import argparse

class PotentiostatReader:
    def __init__(self, com_port, baud_rate=9600, timeout=0.5, package_length=25, output_filename="out_data.txt"):
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.package_length = package_length
        self.output_filename = output_filename
        self.data_block = [b'\x00'] * package_length
        self.start_timestamp = None
        self.serial_connection = None

    def open_serial_connection(self):
        if self.serial_connection is None:
            self.serial_connection = serial.Serial(self.com_port, baudrate=self.baud_rate, timeout=self.timeout)

    def close_serial_connection(self):
        if self.serial_connection is not None:
            self.serial_connection.close()
            self.serial_connection = None

    def validate_data_block(self):
        header = [b'\x04', b'\x68', b'\x13', b'\x13', b'\x68']
        cks = 0
        for x in [int.from_bytes(x, 'big') for x in self.data_block[2:-4]]:
            cks = (cks + x) & 0xFF
        if (self.data_block[-5:] == header and
                self.data_block[0] == b'\x16' and
                int.from_bytes(self.data_block[1], 'big') == cks):
            return True
        return False

    def process_data_block(self):
        data_inv = [x for x in self.data_block[2:-5]]
        data_inv.reverse()
        it = iter(data_inv)
        out_data = [
            int.from_bytes(b''.join([x, next(it)]),
                           byteorder='big',
                           signed=True) for x in it]
        return out_data

    def convert_data(self, out_data):
        gain = 50 / (2**15 - 1)
        to_insert = [str(round(int(x) * gain, 3)) for x in out_data[0:6]]
        temperature = str(round(float(out_data[6]) / 16, 3))
        to_insert.append(temperature)
        return to_insert
    
    def  line_one(self):
        with open(self.output_filename, 'w') as file:
            first_line = "Time/s\tCh1/nA\tCh2/nA\tCh3/nA\tCh4/nA\tCh5/nA\tCh6/nA\tT/°C"
            print(first_line)
            file.write(first_line + "\n")

    def get_data(self):
        self.open_serial_connection()
        accumulated_bytes = b''

        # Accumulate bytes until we have a full package
        while len(accumulated_bytes) < self.package_length:
            # Read remaining bytes to fill the package
            remaining_bytes = self.package_length - len(accumulated_bytes)
            new_data = self.serial_connection.read(remaining_bytes)
            accumulated_bytes += new_data

        if accumulated_bytes:
            # Process the accumulated data
            for byte in accumulated_bytes:
                self.data_block.insert(0, bytes([byte]))
                self.data_block.pop()

            header = [b'\x04', b'\x68', b'\x13', b'\x13', b'\x68']

            cks = 0  # checksum calculation
            # calculating checksum from byte 4 till second to last byte
            for x in [int.from_bytes(x, 'big') for x in self.data_block[2:-4]]:
                cks = (cks + x) & 0xFF

            # validating header, end byte (x16), and checksum
            if self.data_block[-5:] == header \
                    and self.data_block[0] == b'\x16' \
                    and int.from_bytes(self.data_block[1], 'big') == cks:
                # Now process the data
                data_inv = [x for x in self.data_block[2:-5]]
                data_inv.reverse()
                it = iter(data_inv)  # iterator used to fetch 2 bytes
                # Convert pairs of bytes into 16-bit signed integers
                out_data = [
                    int.from_bytes(b''.join([x, next(it)]),
                                byteorder='big',
                                signed=True) for x in it]

                # Convert data to string format for saving
                to_save = [str(x) for x in out_data]
                #print("to_save list:", to_save)  # Debugging: Print the to_save list
                if len(to_save) >= 7:
                    try:
                        # Converting input data to currents in nanoamperes
                        gain = 50 / (2**15 - 1)
                        to_save = [str(round(int(x) * gain, 3)) for x in to_save[0:6]]

                        # Converting temperature to °C
                        """
                        temperature = str(round(float(to_save[6]) / 16, 3))
                        to_save.append(temperature)
                        """
                        # Generating timestamp
                        timestamp = round(time.time(), 4)
                        if self.start_timestamp is None:
                            self.start_timestamp = timestamp
                            delta_time = 0
                        else:
                            delta_time = timestamp - self.start_timestamp
                        to_save.insert(0, str(round(delta_time, 1)))

                        return to_save
                    except ValueError as e:
                        print(f"Error converting temperature: {to_save[6]}, {e}")
                        return None
                else:
                    print("Error: Data block is incomplete:", to_save)
                    return None

        # If data is not valid or is incomplete, return None
        return None



    def run(self):
        data = self.get_data()
        if data is not None:
            with open(self.output_filename, 'a') as file:
                file.write("\t".join(data) + "\n")
        return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Potentiostat Data Reader")
    parser.add_argument("--com_port", type=str, required=True, help="COM port for the potentiostat")
    parser.add_argument("--baud_rate", type=int, default=9600, help="Baud rate for serial communication")
    parser.add_argument("--timeout", type=float, default=0.5, help="Timeout for serial communication")
    parser.add_argument("--package_length", type=int, default=25, help="Expected package length for data")
    parser.add_argument("--output_filename", type=str, default="out_data.txt", help="File to save the output data")

    args = parser.parse_args()  
    reader = PotentiostatReader(
        com_port=args.com_port,
        baud_rate=args.baud_rate,
        timeout=args.timeout,
        package_length=args.package_length,
        output_filename=args.output_filename
    )
    try:
        reader.run()
    except KeyboardInterrupt:
        print("Data collection stopped by user.")
    finally:
        reader.close_serial_connection()