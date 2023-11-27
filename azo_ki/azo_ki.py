import serial
import serial.tools.list_ports as list_ports
from enum import Enum

class KeyboardInterface():

    class commands(Enum):
        # General Commands
        cmd_setup                               = 0x00
        cmd_stop_streaming                      = 0x01
        cmd_stop_serial_comms                   = 0x02

        # IQS7220A
        cmd_iqs7220a_ks                         = 0x10
        cmd_iqs7220a_i2c_read_single            = 0x11
        cmd_iqs7220a_i2c_write_single           = 0x12
        cmd_iqs7220a_i2c_read_multi             = 0x13
        cmd_iqs7220a_i2c_write_multi            = 0x14
        cmd_iqs7220a_stream_ks                  = 0x15
        cmd_iqs7220a_stream_i2c_read_single     = 0x16
        cmd_iqs7220a_stream_i2c_read_multi      = 0x17

        # IQS7320A
        cmd_iqs7320a_ks                         = 0x20
        cmd_iqs7320a_i2c_read_single            = 0x21
        cmd_iqs7320a_i2c_write_single           = 0x22
        cmd_iqs7320a_i2c_read_multi             = 0x23
        cmd_iqs7320a_i2c_write_multi            = 0x24
        cmd_iqs7320a_autonomous_mode            = 0x25
        cmd_iqs7320a_standby_mode               = 0x26
        cmd_iqs7320a_stream_ks                  = 0x27
        cmd_iqs7320a_stream_i2c_read_single     = 0x28
        cmd_iqs7320a_stream_i2c_read_multi      = 0x29

        # IQS9320 - I2C
        cmd_iqs9320_i2c_read_single             = 0x30
        cmd_iqs9320_i2c_write_single            = 0x31
        cmd_iqs9320_i2c_read_multi              = 0x32
        cmd_iqs9320_i2c_write_multi             = 0x33
        cmd_iqs9320_stream_i2c_read_single      = 0x34
        cmd_iqs9320_stream_i2c_read_multi       = 0x35

        # IQS9320 - Key Scan
        cmd_iqs9320_ks                          = 0x40
        cmd_iqs9320_ks_i2c_read_single          = 0x41
        cmd_iqs9320_ks_i2c_write_single         = 0x42
        cmd_iqs9320_ks_i2c_read_multi           = 0x43
        cmd_iqs9320_ks_i2c_write_multi          = 0x44
        cmd_iqs9320_ks_standby                  = 0x45
        cmd_iqs9320_ks_stream_ks                = 0x46
        cmd_iqs9320_ks_stream_i2c_read_single   = 0x47
        cmd_iqs9320_ks_stream_i2c_read_multi    = 0x48

    class device_select_e(Enum):
        device_iqs7220a     = 0
        device_iqs7320a     = 1
        device_iqs9320_i2c  = 2
        device_iqs9320_ks   = 3

    # ------------------------------------
    # Constructor, Destructor, other helper functions
    # ------------------------------------

    def __init__(self, platform, num_columns=1, num_rows=1, device_address=None):
        self.__pid          = [0xF00A, 0x000A, 0xCAFE]
        self.__vid          = [0x2E8A, 0x239A]
        self.packet_byte_a  = 0xCC
        self.packet_byte_b  = 0xEF
        self.command_id     = 0
        self.platform       = platform
        self.num_columns    = num_columns
        self.num_rows       = num_rows
        self.device_address = device_address

        self.num_devices = self.num_columns * self.num_rows

        if self.__find_devices():
            print("Connected to Raspberry Pi Pico W")
        else:
            raise Exception("Unable to connect to Raspberry Pi Pico W")

        self.setup(platform, num_columns, num_rows)

    def __del__(self):
        try:
            self.stop_serial_comms()
            self.serial_conn.close()
        except:
            pass

    def __find_devices(self):
        for port in list_ports.comports():
            print(port, ", pid = ", port.pid, ", vid = ", port.vid)
            if (port.vid in self.__vid and port.pid in self.__pid):
                self.serial_conn = serial.Serial(port.device, baudrate=115200, timeout=0.5)
                print("Serial port open")
                return True
        return False
    
    def get_crc(self, data_array):
        crc = 0xFFFF
        j = 0

        for byte in data_array:
            crc = crc ^ ((byte) << 8)
            crc = crc & 0xFFFF

            j = 0
            while j < 8:
                if crc & 0x8000:
                    crc = crc << 1 ^ 0x1021
                    crc = crc & 0xFFFF
                else:
                    crc = crc << 1
                    crc = crc & 0xFFFF
                j += 1
        
        return crc
    
    def send_command(self, command_bytes):
        # Get 8-bit command ID
        self.command_id += 1
        if self.command_id > 0xFF:
            self.command_id = 0

        # Compile packet
        total_packet = [
                        self.packet_byte_a,
                        self.packet_byte_b,
                        len(command_bytes)+1,
                        self.command_id
                        ]
        for byte in command_bytes:
            total_packet.append(byte)

        # Now calculate the CRC for the packet excluding Start of Frame and Packet Length
        crc_value = self.get_crc(total_packet[3:])
        total_packet.append(crc_value & 0xFF)
        total_packet.append((crc_value & 0xFF00) >> 8)
        total_packet.append(self.packet_byte_a)
        total_packet.append(self.packet_byte_b)

        # Write packet
        self.serial_conn.read_all()
        self.serial_conn.write(total_packet)

        # Await packet response
        await_A = True
        bytes_read = 0
        while(await_A):
            read_value = int(self.serial_conn.read()[0])
            bytes_read += 1
            if read_value == self.packet_byte_a:
                await_A = False
            if bytes_read > 100:
                raise Exception("Failed to receive response packet from device")
        read_values = self.serial_conn.read(5)
        read_values = [int(x) for x in read_values]

        # Verify packet
        if(len(read_values) == 5):
            packet_fail = False
            if not (read_values[0] == self.packet_byte_b):
                print("\033[91m Byte B 1 error \033[0m")
                packet_fail = True
            if not (read_values[1] == self.command_id):
                print("\033[91m ID error \033[0m")
                print("\033[91m Expected : {} \033[0m".format(self.command_id))
                print("\033[91m Received : {} \033[0m".format(read_values[1]))
                packet_fail = True
            if not (read_values[2] == command_bytes[0]):
                print("\033[91m command error \033[0m")
                packet_fail = True
            if not (read_values[3] == self.packet_byte_a):
                print("\033[91m Byte A 2 error \033[0m")
                packet_fail = True
            if not (read_values[4] == self.packet_byte_b):
                print("\033[91m Byte B 2 error \033[0m")
                packet_fail = True
        else:
            print("\033[91m Serial timeout \033[0m")
            packet_fail = True
        if packet_fail:
            raise Exception("Packet transmission failed : {} : {}".format(self.command_id, command_bytes[0]))

    def generic_return(self):
        read_values = self.serial_conn.read(4)
        read_values = [int(x) for x in read_values]
        if (len(read_values) == 4):
            valid_read = True
            for i in range(4):
                if (read_values[i] != 0xFF):
                    valid_read = False
                    break
        else:
            valid_read = False
        if not valid_read:
            print("\033[91m Invalid response from RP Pi Pico \033[0m")
            raise Exception("Invalid response from RP Pi Pico")

    # ------------------------------------
    # Generic Functions
    # ------------------------------------
    
    def setup(self, device:device_select_e, num_columns:int=0, num_rows:int=0):
        self.send_command(
            [
            int(self.commands.cmd_setup.value),
            device.value,
            num_columns,
            num_rows
            ]
        )

    def stop_streaming(self):
        self.send_command(
            [
            int(self.commands.cmd_stop_streaming.value),
            ]
        )

    def stop_serial_comms(self):
        self.send_command(
            [
            int(self.commands.cmd_stop_serial_comms.value),
            ]
        )

    # ------------------------------------
    # IQS7220A
    # ------------------------------------

    def iqs7220a_ks(self):
        self.send_command(
            [
            int(self.commands.cmd_iqs7220a_ks)
            ]
        )
        read_values = self.serial_conn.read(self.num_devices)
        read_values = [int(x) for x in read_values]
        return read_values
    
    def iqs7220a_i2c_read_single(self, device_select, register_addr, num_bytes, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        self.send_command([
            int(self.commands.cmd_iqs7220a_i2c_read_single.value),
            device_select,
            device_addr,
            register_addr,
            num_bytes
        ])
        read_values = self.serial_conn.read(num_bytes)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs7220a_i2c_write_single(self, device_select, register_addr, bytes_array:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        command = [
            int(self.commands.cmd_iqs7220a_i2c_write_single.value),
            device_select,
            device_addr,
            register_addr,
            len(bytes_array)
        ]
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs7220a_i2c_read_multi(self, register_addr, num_bytes, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        self.send_command([
            int(self.commands.cmd_iqs7220a_i2c_read_multi.value),
            device_addr,
            register_addr,
            num_bytes
        ])
        read_values = self.serial_conn.read(num_bytes*self.num_devices)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs7220a_i2c_write_multi(self, register_addr, bytes_array:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        command = [
            int(self.commands.cmd_iqs7220a_i2c_write_multi.value),
            device_addr,
            register_addr,
            len(bytes_array)
        ]
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs7220a_stream_ks(self, report_interval_ms):
        self.send_command(
            [
            int(self.commands.cmd_iqs7220a_stream_ks.value),
            report_interval_ms
            ]
        )
        self.generic_return()

    def iqs7220a_stream_i2c_read_single(self, report_interval_ms, device_select, register_addr:list, num_bytes:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs7220a_stream_i2c_read_single.value),
            report_interval_ms,
            device_select,
            device_addr,
            len(register_addr)
        ]
        for x in register_addr:
            command.append(x)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()

    def iqs7220a_stream_i2c_read_multi(self, report_interval_ms, register_addr:list, num_bytes:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs7220a_stream_i2c_read_multi.value),
            report_interval_ms,
            device_addr,
            len(register_addr)
        ]
        for x in register_addr:
            command.append(x)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()

    # ------------------------------------
    # IQS7320A
    # ------------------------------------

    def iqs7320a_ks(self):
        self.send_command(
            [
            int(self.commands.cmd_iqs7320a_ks)
            ]
        )
        read_values = self.serial_conn.read(self.num_devices)
        read_values = [int(x) for x in read_values]
        return read_values
    
    def iqs7320a_i2c_read_single(self, device_select, register_addr, num_bytes, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        self.send_command([
            int(self.commands.cmd_iqs7320a_i2c_read_single.value),
            device_select,
            device_addr,
            register_addr,
            num_bytes
        ])
        read_values = self.serial_conn.read(num_bytes)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs7320a_i2c_write_single(self, device_select, register_addr, bytes_array:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        command = [
            int(self.commands.cmd_iqs7320a_i2c_write_single.value),
            device_select,
            device_addr,
            register_addr,
            len(bytes_array)
        ]
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs7320a_i2c_read_multi(self, register_addr, num_bytes, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        self.send_command([
            int(self.commands.cmd_iqs7320a_i2c_read_multi.value),
            device_addr,
            register_addr,
            num_bytes
        ])
        read_values = self.serial_conn.read(num_bytes*self.num_devices)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs7320a_i2c_write_multi(self, register_addr, bytes_array:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        command = [
            int(self.commands.cmd_iqs7320a_i2c_write_multi.value),
            device_addr,
            register_addr,
            len(bytes_array)
        ]
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs7320a_autonomous(self, selection_bool:bool):
        if selection_bool == True:
            selection = 2
        elif selection_bool == False:
            selection = 1
        self.send_command(
            [
            int(self.commands.cmd_iqs7320a_autonomous_mode.value),
            selection
            ]
        )
        self.generic_return()

    def iqs7320a_standby(self, selection_bool:bool):
        if selection_bool == True:
            selection = 2
        elif selection_bool == False:
            selection = 1
        self.send_command(
            [
            int(self.commands.cmd_iqs7320a_standby_mode.value),
            selection
            ]
        )
        self.generic_return()

    def iqs7320a_stream_ks(self, report_interval_ms):
        self.send_command(
            [
            int(self.commands.cmd_iqs7320a_stream_ks.value),
            report_interval_ms
            ]
        )
        self.generic_return()

    def iqs7320a_stream_i2c_read_single(self, report_interval_ms, device_select, register_addr:list, num_bytes:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs7320a_stream_i2c_read_single.value),
            report_interval_ms,
            device_select,
            device_addr,
            len(register_addr)
        ]
        for x in register_addr:
            command.append(x)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()

    def iqs7320a_stream_i2c_read_multi(self, report_interval_ms, register_addr:list, num_bytes:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs7320a_stream_i2c_read_multi.value),
            report_interval_ms,
            device_addr,
            len(register_addr)
        ]
        for x in register_addr:
            command.append(x)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()

    # ------------------------------------
    # IQS9320 I2C
    # ------------------------------------

    def iqs9320_i2c_read_single(self, register_addr, num_bytes, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        self.send_command([
            int(self.commands.cmd_iqs9320_i2c_read_single.value),
            device_addr,
            register_addr & 0xFF,
            (register_addr & 0xFF00) >> 8,
            num_bytes
        ])
        read_values = self.serial_conn.read(num_bytes)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs9320_i2c_write_single(self, register_addr, bytes_array:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        command = [
            int(self.commands.cmd_iqs9320_i2c_write_single.value),
            device_addr,
            register_addr & 0xFF,
            ((register_addr & 0xFF00) >> 8),
            len(bytes_array)
        ]
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs9320_i2c_read_multi(self, device_addresses:list, register_addr, num_bytes):
        command = [
            int(self.commands.cmd_iqs9320_i2c_read_multi.value),
            len(device_addresses)
        ]
        for addr in device_addresses:
            command.append(addr)
        command.append(register_addr & 0xFF)
        command.append((register_addr & 0xFF00) >> 8)
        command.append(num_bytes)
        self.send_command(command)
        read_values = self.serial_conn.read(num_bytes*len(device_addresses))
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs9320_i2c_write_multi(self, device_addresses:list, register_addr, bytes_array:list):
        command = [
            int(self.commands.cmd_iqs9320_i2c_write_multi.value),
            len(device_addresses)
        ]
        for addr in device_addresses:
            command.append(addr)
        command.append(register_addr & 0xFF)
        command.append((register_addr & 0xFF00) >> 8)
        command.append(len(bytes_array))
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs9320_stream_i2c_read_single(self, report_interval_ms, register_addr:list, num_bytes:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs9320_stream_i2c_read_single.value),
            report_interval_ms,
            device_addr,
            len(register_addr)
        ]
        for x in register_addr:
            command.append(x & 0xFF)
            command.append((x & 0xFF00) >> 8)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()

    def iqs9320_stream_i2c_read_multi(self, report_interval_ms, device_addr:list, register_addr:list, num_bytes:list):
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs9320_stream_i2c_read_multi.value),
            report_interval_ms,
            len(device_addr)
        ]
        for x in device_addr:
            command.append(x)
        command.append(len(register_addr))
        for x in register_addr:
            command.append(x & 0xFF)
            command.append((x & 0xFF00) >> 8)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()

    # ------------------------------------
    # IQS9320 Key Scan
    # ------------------------------------

    def iqs9320_ks(self, num_channels):
        self.send_command(
            [
            int(self.commands.cmd_iqs9320_ks.value),
            int(num_channels)
            ]
        )
        read_values = self.serial_conn.read(self.num_devices*3)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs9320_ks_i2c_read_single(self, device_select, register_addr, num_bytes, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        self.send_command([
            int(self.commands.cmd_iqs9320_ks_i2c_read_single.value),
            device_select,
            device_addr,
            register_addr & 0xFF,
            (register_addr & 0xFF00) >> 8,
            num_bytes
        ])
        read_values = self.serial_conn.read(num_bytes)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs9320_ks_i2c_write_single(self, device_select, register_addr, bytes_array:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        command = [
            int(self.commands.cmd_iqs9320_ks_i2c_write_single.value),
            device_select,
            device_addr,
            register_addr & 0xFF,
            (register_addr & 0xFF00) >> 8,
            len(bytes_array)
        ]
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs9320_ks_i2c_read_multi(self, register_addr, num_bytes, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        self.send_command([
            int(self.commands.cmd_iqs9320_ks_i2c_read_multi.value),
            device_addr,
            register_addr & 0xFF,
            (register_addr & 0xFF00) >> 8,
            num_bytes
        ])
        read_values = self.serial_conn.read(num_bytes*self.num_devices)
        read_values = [int(x) for x in read_values]
        return read_values

    def iqs9320_ks_i2c_write_multi(self, register_addr, bytes_array:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        command = [
            int(self.commands.cmd_iqs9320_ks_i2c_write_multi.value),
            device_addr,
            register_addr & 0xFF,
            (register_addr & 0xFF00) >> 8,
            len(bytes_array)
        ]
        for byte in bytes_array:
            command.append(byte)
        self.send_command(command)
        self.generic_return()

    def iqs9320_ks_standby(self, selection_bool:bool):
        if selection_bool == True:
            selection = 2
        elif selection_bool == False:
            selection = 1
        self.send_command(
            [
            int(self.commands.cmd_iqs9320_ks_standby.value),
            selection
            ]
        )
        self.generic_return()
    
    def iqs9320_ks_stream_ks(self, report_interval_ms, num_channels):
        self.send_command(
            [
            int(self.commands.cmd_iqs9320_ks_stream_ks.value),
            report_interval_ms,
            num_channels
            ]
        )
        self.generic_return()

    def iqs9320_ks_stream_i2c_read_single(self, report_interval_ms, device_select, register_addr:list, num_bytes:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs9320_ks_stream_i2c_read_single.value),
            report_interval_ms,
            device_select,
            device_addr,
            len(register_addr)
        ]
        for x in register_addr:
            command.append(x & 0xFF)
            command.append((x & 0xFF00) >> 8)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()

    def iqs9320_ks_stream_i2c_read_multi(self, report_interval_ms, register_addr:list, num_bytes:list, device_addr=None):
        if device_addr == None:
            device_addr = self.device_address
            if device_addr == None:
                raise Exception("No device address selected")
        if (len(register_addr) != len(num_bytes)):
            raise Exception("Number of register addresses and read length is not equal")
        command = [
            int(self.commands.cmd_iqs9320_ks_stream_i2c_read_multi.value),
            report_interval_ms,
            device_addr,
            len(register_addr)
        ]
        for x in register_addr:
            command.append(x & 0xFF)
            command.append((x & 0xFF00) >> 8)
        for x in num_bytes:
            command.append(x)
        self.send_command(command)
        self.generic_return()


