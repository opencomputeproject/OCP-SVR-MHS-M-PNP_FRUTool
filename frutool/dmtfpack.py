# SPDX-FileCopyrightText: 2025 Hewlett Packard Enterprise Development LP
# SPDX-License-Identifier: MIT

# Pack DMTF FRU Files Format 
# This module provides functions to pack DMTF FRU files format as per DSP0220 specification.
# It includes functions to build the File Descriptor Table (FDT) and pack FDT entries.

import os
import sys
import struct
import uuid
import json

from utility import *

###################################################################
# Constants

# Define FRU header parameters.
DMTF_FRU_IDENTIFIER = 0x1AB4  # 2 bytes
DMTF_FRU_VERSION    = 1       # 1 byte

# DMTF FRU HEADER
# That packs: identifier (H = 2 bytes), version (B = 1 byte),  file_count (B = 1 byte),reserved (I = 4 bytes).
# However, note that in "<HBBI" the last field is B (1 byte) so total size becomes: 2+1+1+4 = 8 bytes.
DMTF_FRU_HEADER_FORMAT = "<HBBI"  # identifier (H), version (B), reserved (I), file_count (B)
DMTF_FRU_HEADER_SIZE = struct.calcsize(DMTF_FRU_HEADER_FORMAT)  # should be 8 bytes

# DMTF FRU FDT ENTRY
 # format ID (16s), version (I), size (I), offset (I), flags (H), reserved (H), context (I), checksum (I)
FDT_ENTRY_FORMAT = "<16sIIIHHII" 
FDT_ENTRY_SIZE = 40  #should always be 40 bytes per spec


# Default format identifiers in hex format
DMTF_GENERAL_FRU_RECORD_FILE =  "a4f59e2c-b8a9-4fad-b092-41332c90e65b"

# Default FDT entries
DEFAULT_FDT_ENTRY_FLAGS  = 0
DEFAULT_FDT_ENTRY_CONTEXT = 0

###################################################################
# Classes


# FDT entry contents from DSP0220
class FdtEntry:
    def __init__(self, formatId = DMTF_GENERAL_FRU_RECORD_FILE, version = 0, size = 0, offset = 0, flags = 0, context = 0, checksum = 0):
        self.formatId = formatId
        self.version = version
        self.size = size
        self.offset = offset
        self.flags = flags
        self.context = context
        self.checksum = checksum

    def __str__(self):
        return f"{self.formatId}({self.version})({self.size})({self.offset})({self.flags})({self.context})"

###################################################################
# packing functions


# Create the FD for n number of files provided in input_files.
def build_fdt( input_files, fdt_list, verbose=False):
    """
    Builds a File Descriptor Table (FDT) for a set of input files according to the DMTF FRU specification.
    Each entry in the FDT contains metadata about a file, including its size, offset, and CRC32 checksum.
    The offset for each file is calculated based on the number of files, the size of each FDT entry, and the size of the DMTF FRU header.
    Args:
        input_files (list of str): List of file paths to be included in the FDT.
        fdt_list (list): List of FDT entry objects corresponding to each input file.
        verbose (bool, optional): If True, prints detailed information during processing. Defaults to False.
    Returns:
        list: A list of packed FDT entries representing the file descriptor table.
    Raises:
        SystemExit: If any file in input_files does not exist or is not a valid file.
    """

    # FDT is a list of packed entries
    file_descriptor_table = []

    file_count = len(input_files)

    # The DMTF DSP0220 spec says the offset is number of bytes between the the first byte of
    # the FRU Files Record Header and the first byte of the FRU File
    # each FDT is 40 bytes so it is just number of files * 40B
    # plus the DMTF FRU header which is 8B
    file_offset = file_count * FDT_ENTRY_SIZE + DMTF_FRU_HEADER_SIZE

    if verbose:
        print(f"End of FDT Offset: 0x{file_offset:x}")

    index = 0

    # Iterate through input files to get params
    for file in input_files:

        fdt_obj = fdt_list[index]

        # Ensure file is present and valid
        if not os.path.isfile(file):
            print(f"Error: {file} is not a valid file.")
            sys.exit(1)

        # Calculate file size and offset then add to fdt object
        # Use the size from FDT object if it's already set (for compressed files)
        # Otherwise, get the file size from disk
        if fdt_obj.size > 0:
            file_size = fdt_obj.size  # Use pre-calculated size (e.g., for compressed files)
        else:
            file_size = os.path.getsize(file)  # Calculate from file on disk
 
        if verbose:    
            print(f"File Size: 0x{file_size:x}")
            print(f"File Offset: 0x{file_offset:x}")

        fdt_obj.size = file_size
        fdt_obj.offset = file_offset        

        checksum = calculate_crc32_file(file)

        if verbose:            
            print(f"Checksum: 0x{checksum:x}")


        fdt_obj.checksum = checksum
        new_entry = pack_fdt_entry(fdt_obj)
        file_descriptor_table.append(new_entry)
        index += 1
        # Bump the file offset to the next offset after this file
        file_offset += file_size

    if verbose:
        print(f"fdt size {len(file_descriptor_table)}")

    return file_descriptor_table


# Pack FDT entry - returned byte packed FDT entry
def pack_fdt_entry(fdt_obj, verbose=False):
    """
    Packs a Firmware Device Table (FDT) entry into a binary format.
    Args:
        fdt_obj: An object containing FDT entry attributes:
            - formatId (str): GUID string representing the entry's unique identifier.
            - version (int): Version number of the entry.
            - size (int): Size of the file associated with the entry.
            - offset (int): Offset of the file in the firmware image.
            - flags (int): Flags associated with the entry.
            - context (int): Context value for the entry.
            - checksum (int): Checksum of the entry data.
        verbose (bool, optional): If True, prints debug information during packing. Defaults to False.
    Returns:
        bytes: The packed FDT entry as a bytes object.
    Raises:
        ValueError: If the GUID string is invalid.
        struct.error: If packing fails due to incorrect data types or values.
    """

    guid_string = fdt_obj.formatId
    version = fdt_obj.version
    file_size = fdt_obj.size
    file_offset = fdt_obj.offset
    flags = fdt_obj.flags
    context = fdt_obj.context
    checksum = fdt_obj.checksum    

    if verbose:
        print("packing entry")

    uuid_obj = uuid.UUID(guid_string)
    
    if verbose:      
        print(uuid_obj)

    uuidbytes = uuid_obj.bytes

    if verbose:    
        print(f"UUID BYTES: {uuidbytes}")

    #pack the FDT entry as per "<16sIIIHHII" format
    new_entry = struct.pack(FDT_ENTRY_FORMAT, uuidbytes, version, file_size, file_offset,flags,0,context,checksum)

    if verbose:  
        print(f"FDT Entry: {new_entry}")
    return new_entry


###################################################################

# Parse DMTF JSON function takes in the json input file and returns a list of fdt input structure.
def parse_dmtf_json(json_input_file, verbose=False):
    """
    Parses a DMTF JSON file and extracts file information and FDT entries.
    Args:
        json_input_file (str): Path to the JSON input file containing DMTF data.
        verbose (bool, optional): If True, prints detailed parsing information. Defaults to False.
    Returns:
        tuple:
            file_list (list of str): List of filenames extracted from the JSON.
            fdt_list (list of FdtEntry): List of FdtEntry objects created from the JSON data.
    Raises:
        SystemExit: If required fields such as 'Filename' or 'FormatIdentifier' are missing or empty.
    The function expects the JSON file to contain a 'Files' key with a list of file dictionaries.
    Each file dictionary should include 'Filename', 'FormatIdentifier', 'FormatVersion', 'Flags', and 'Context'.
    Flags are packed into an integer according to their values.
    """

    fdt_list = []
    file_list = []

    # Parse JSON from a file
    with open(json_input_file, "r") as file:
        python_dict_from_file = json.load(file)

    if verbose:  
        print(python_dict_from_file)

    for file  in python_dict_from_file['Files']:
        # Filename must be there and not empty
        if file["Filename"]:
            
            if verbose: 
                print(file["Filename"])

            file_list.append(file["Filename"])
        else:
            print(f"Filename must be present - exiting!")
            sys.exit(1)            

        # Format identifier must be present
        if file["FormatIdentifier"]:        
            fid = file["FormatIdentifier"]
        else:
            print(f"Format ID must be present - exiting!")
            sys.exit(1)    

        # If version is not present then it is assumed to be 0
        ver = 0
        if file["FormatVersion"]:
            ver = file["FormatVersion"]


        resident = False
        dynamic =  False
        checksum = False
        compression = "none"

        # Make sure flags are present in the json
        if file["Flags"]:
            resident = file["Flags"]["Resident"]
            dynamic = file["Flags"]["Dynamic"]
            checksum = file["Flags"]["ChecksumPresent"]
            compression = file["Flags"]["Compression"]

        context = file["Context"]

        # Pack the flags
        flags = 0

        if checksum:
            flags |= 0b0100

        if dynamic:
            flags |= 0b10000

        if resident:
           flags |= 0b100000

        if compression == "gzip":
            flags |= 0b0010
        elif compression == "messagepack":
            flags |= 0b0001
        elif compression == "another":
            flags |= 0b0011

        fdt = FdtEntry(fid,ver,resident,0,flags,context)
        
        if verbose:        
            print(fdt)

        fdt_list.append(fdt)

    if verbose:    
        print(f"File List: {file_list}")

    return file_list, fdt_list
