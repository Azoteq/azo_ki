# Introduction

Developed for interaction with the Azoteq KeyboardInterface Arduino project.

# Examples

## IQS9320 I2C Example
```
from azo_ki import KeyboardInterface

# Initialise class object
ki = KeyboardInterface(
        KeyboardInterface.device_select_e.device_iqs9320_i2c, 
        device_address=0x30
    )

# Read address 0x2000 for 2 bytes
data = ki.iqs9320_i2c_read_single(0x2000, 2)

# Write to address 0x2000
ki.iqs9320_i2c_write_single(0x2000, [0x10, 0x00])

# Read from multiple devices
data = ki.iqs9320_i2c_read_multi([0x30, 0x32, 0x34], 0x2000, 2)

# Write to multiple devices
ki.iqs9320_i2c_write_multi([0x30, 0x32, 0x34], 0x2000, [0x10, 0x00])

# Stream from single device
ki.iqs9320_stream_i2c_read_single(50, [0x1000, 0x2000], [4, 2])
for i in range(sample_size):
    data = ki.serial_conn.read(4+2)
    data_1 = data[0:4] # 0x1000 Data
    data_2 = data[4:6] # 0x2000 Data

# Stream from multiple devices
ki.iqs9320_stream_i2c_read_multi(50, [0x30, 0x32, 0x34], [0x1000, 0x2000], [4, 2])
for i in range(sample_size):
    data = ki.serial_conn.read(3*(4+2))
    data_1_1 = data[0:4]    # 0x1000 data for device 0x30
    data_1_2 = data[4:8]    # 0x1000 data for device 0x32
    data_1_3 = data[8:12]   # 0x1000 data for device 0x34
    data_2_1 = data[12:14]  # 0x2000 data for device 0x30
    data_2_2 = data[14:16]  # 0x2000 data for device 0x32
    data_2_3 = data[16:18]  # 0x2000 data for device 0x34
```

## IQS7220A Example
```
from azo_ki import KeyboardInterface

# Initialise class object
ki = KeyboardInterface(
        KeyboardInterface.device_select_e.device_iqs7220a,
        num_columns=2,
        num_rows=2,
        device_address=0x56
    )

# Key scan single device
data = ki.iqs7220a_ks()
device_reset = data[0] & 0x1
channel_0 = (data[0] & 0x2) >> 1
channel_1 = (data[0] & 0x4) >> 2
channel_2 = (data[0] & 0x8) >> 3
channel_3 = (data[0] & 0x10) >> 4

# Read address 0x10 for 2 bytes from device in the 1st column and 2nd row
data = ki.iqs7220a_i2c_read_single(1, 0x10, 2)

# Write to address 0x10 to device in the 2nd column and 1st row.
ki.iqs7220a_i2c_write_single(2, 0x10, [0x00, 0x10])

# Stream I2C data from all devices in the matrix
ki.iqs7220a_steam_i2c_read_multi(50, [0x10, 0x20], [2, 4])
for i in range(sample_size):
    data = ki.serial_conn.read((2*2)*(2+4))
    data_1_1 = data[0:2]    # 0x10 data for col 1 row 1
    data_1_2 = data[2:4]    # 0x10 data for col 1 row 2
    data_1_3 = data[4:6]    # 0x10 data for col 2 row 1
    data_1_4 = data[6:8]    # 0x10 data for col 2 row 2
    data_2_1 = data[8:12]   # 0x20 data for col 1 row 1
    data_2_2 = data[12:16]  # 0x20 data for col 1 row 2
    data_2_3 = data[16:20]  # 0x20 data for col 2 row 1
    data_2_4 = data[20:24]  # 0x20 data for col 2 row 2
```