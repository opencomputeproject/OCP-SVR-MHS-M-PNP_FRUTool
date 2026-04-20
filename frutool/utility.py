# SPDX-FileCopyrightText: 2026 Hewlett Packard Enterprise Development LP
# SPDX-License-Identifier: MIT

# Library of useful utility functions

import json
import sys
import struct
import zlib
from ctypes import *    # crc16
import jsonschema

###########################################################
# Constants
g_endian_type = "<"           # All FRU data numbers must be LITTLE endian format


###########################################################
# Utility functions

# exit
def exitProgram(var):
    sys.exit(var)
        
# C-like printf
def printf(fmt, *args):
    sys.stdout.write(fmt % args)

# C-like sprintf
def sprintf(fmt, *args):
    return fmt % tuple(args)


# Dump hexidecimal formatted data bytes.
def hexdump(label, myBytes, offset, numBytes, verbose = False):
    """
    Generates a formatted hexadecimal dump of a byte sequence, similar to the output of the Unix `hexdump` utility.
    Args:
        label (str): A label to include in the output header.
        myBytes (bytes or bytearray): The byte sequence to be dumped.
        offset (int): The starting offset to display in the output.
        numBytes (int): The number of bytes from `myBytes` to include in the dump.
        verbose (bool, optional): If True, prints the hexdump to stdout. Defaults to False.
    Returns:
        str: The formatted hexdump string.
    Notes:
        - Duplicate lines are replaced with a single '*' line to save space.
        - Each line displays the offset, hexadecimal representation, and printable ASCII characters.
        - Non-printable characters are replaced with '.' in the ASCII section.
    """

    fullLine = 16
    halfLine = 8
    lineLast=""
    lineCurrent=""
    isHiddenLine = False
    
    FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
    lines = []
    for c in range(0, numBytes, fullLine):

        # First 8 characters
        chars1 = myBytes[c:c+halfLine]
        hex1 = ' '.join(["%02x" % x for x in chars1])
        # Second 8 characters
        chars2 = myBytes[c+halfLine:c+fullLine]
        hex2 = ' '.join(["%02x" % x for x in chars2])
        charsAll = myBytes[c:c+fullLine]

        # Save space by not printing duplicate data
        lineCurrent = ''.join(hex1) + " " + ''.join(hex2)
        if lineCurrent == lineLast:
            if isHiddenLine == False:
                lines.append("*\n")
            isHiddenLine = True
            continue
        isHiddenLine = False    
        lineLast = lineCurrent

        # Postable human readable content
        printable = ''.join(["%s" % ((x <= 127 and FILTER[x]) or '.') for x in charsAll])
        # Append the new line to list
        lines.append("%08X  %-*s %-*s|%s|\n" % (c+offset, halfLine*3, hex1.upper(), halfLine*3, hex2.upper(), printable))

    if isHiddenLine:
        lines.append("%08X  %-*s %-*s|%s|\n" % (c+offset, halfLine*3, hex1.upper(), halfLine*3, hex2.upper(), printable))
    myhex = ''.join(lines)  # create one big string
    buf = sprintf("HEXDUMP: %s (bytes=%d)\n%s\n", label, numBytes, myhex)

    if verbose:
        printf("%s", buf)

    return buf


# Compute IPMI area checksum
def computeZeroChecksum(myBytes, offStart, offEnd):
    #breakpoint()
    cs = c_uint(0)
    for ix in range(offStart,offEnd):
        cs.value = (cs.value + myBytes[ix]) & 0xFF
    cs.value = (-cs.value) & 0xFF
    return cs.value

# Return pad bytes required to make area length be an even multiple of 8.
def getPadBytes(off):
    pad=0
    if off%8:
        pad = (int(off/8)+1)*8 - off
    return pad


# Append value to bytearray buffer
def appendByteBuf(byteBuf, inVal, offset, isType, numVal=1):
    """
    Appends a value to a byte buffer at a specified offset using a given type.
    Parameters:
        byteBuf (bytearray or memoryview): The buffer to append data to.
        inVal (any): The value to append. Type depends on `isType`.
        offset (int): The offset in the buffer where the value should be appended.
        isType (type or str): The type of the value to append. Supported types are:
            - type(b'') or "bytes": bytes
            - type("") or "str": string (will be encoded to bytes)
            - "ulong": unsigned long (4 bytes)
            - "uint": unsigned int (4 bytes)
            - "ushort": unsigned short (2 bytes)
            - "uchar": unsigned char (1 byte)
        numVal (int, optional): Number of values to append for numeric types. Defaults to 1.
    Returns:
        int: The number of bytes appended to the buffer, or 0 if the type is unknown.
    Raises:
        ValueError: If the value cannot be packed into the buffer at the specified offset.
    Notes:
        - Uses global variable `g_endian_type` to determine endianness for struct packing.
        - On error, prints a hexdump of the buffer segment and an error message.
    """

    #values = (b'abcdefghijklmnop')
    # []=list, {}=dict, ()=tuple, b''=bytes
    if isType==type(b'') or isType=="bytes":
        sz = len(inVal)
        fmt = g_endian_type + str(sz) + 's'
    elif isType==type("") or isType=="str":
        inVal = str.encode(inVal)
        sz = len(inVal)
        fmt = g_endian_type + str(sz) + 's'
    elif isType == "ulong":
        sz = 4 
        fmt = g_endian_type + str(numVal) + 'L'  # unsigned long (4 bytes each)
    elif isType == "uint":
        sz = 4 
        fmt = g_endian_type + str(numVal) + 'I'  # unsigned int (4 bytes each)
    elif isType == "ushort":
        sz = 2 
        fmt = g_endian_type + str(numVal) + 'H'  # unsigned short (2 bytes each)
    elif isType == "uchar":
        sz = 1
        fmt = g_endian_type + str(numVal) + 'B'  # unsigned char (1 bytes each)
    else:
        print(f"Unknown type= {isType}")
        return 0

    try:
        struct.pack_into(fmt,byteBuf,offset,inVal)
    except ValueError:
        hexdump("Append byteBuf",byteBuf.raw[offset:offset+sz],offset,sz)
        print("Can't append ByteBuf\n")
    
    return sz

###############################################################################################

# Calculate the checksum of a file
def calculate_crc32_file(filepath, verify=False):
    """
    Calculates the CRC32 checksum of a file.
    Args:
        filepath (str): The path to the file for which to calculate the CRC32 checksum.
        verify (bool, optional): If True, prints the CRC32 value in 8-digit hexadecimal format. Defaults to False.
    Returns:
        int or None: The CRC32 checksum as an integer if successful, or None if the file is not found or an error occurs.
    Raises:
        FileNotFoundError: If the specified file does not exist.
        Exception: For any other errors encountered during file reading or CRC calculation.
    """

    # Open the file
    try:
        with open(filepath, 'rb') as file:
            data = file.read()
            crc32_value = zlib.crc32(data)
            
            if verify:                
                print(f'{crc32_value:08x}')  # Format as 8-digit hexadecimal            
            
            return crc32_value           

    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

###############################################################################################

# Validate a JSON file against a JSON schema
def validate_json_with_schema(json_file, schema_file):
    """
    Validates a JSON input file against a JSON schema file.
    Args:
        json_file (str): Path to the JSON input file to validate.
        schema_file (str): Path to the JSON schema file.
    Returns:
        tuple:
            valid (bool): True if validation passed, False otherwise.
            message (str): Descriptive message indicating pass or failure details.
    """
    try:
        with open(json_file, "r") as f:
            json_data = json.load(f)
    except FileNotFoundError:
        return False, f"Input file not found: {json_file}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in input file {json_file}: {e}"

    try:
        with open(schema_file, "r") as f:
            schema_data = json.load(f)
    except FileNotFoundError:
        return False, f"Schema file not found: {schema_file}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in schema file {schema_file}: {e}"

    try:
        jsonschema.validate(instance=json_data, schema=schema_data)
        return True, f"Validation passed: {json_file}"
    except jsonschema.ValidationError as e:
        return False, f"Validation failed for {json_file}: {e.message}"
    except jsonschema.SchemaError as e:
        return False, f"Schema error in {schema_file}: {e.message}"


# Convert a hex string 's' to a hex number
def hexToNum(s):
    try:
        hexnum = int(s,16)
        return False, hexnum
    except ValueError:
        return True, 0