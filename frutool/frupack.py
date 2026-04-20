# SPDX-FileCopyrightText: 2026 Hewlett Packard Enterprise Development LP
# SPDX-License-Identifier: MIT

# FRUpack.py
# Enhanced tool to create full FRU EEPROM image binary file from input files with gzip support
# will create the ipmi fru and the DMTF fru image
# Inputs:
#   ipmi json file e.g.  ipmi.json
#   dmtf fru files input json e.g. dmtf_fru.json
#   which contains intputs for DMTF FRU image as per DSP0220
#
# Outputs:
#   Full image file as per DSP0220 shown in figure 2
#
# Builds:
#   IPMI header
#   Board Area Info Record if in input JSON
#   Chassis Info Record if in input JSON
#   Product Area Info Record if in input JSON
#   DMTF OEM Record in Multi-record section
#   Creates IPMI and DMTF FRU image 
#   Outputs full image combined from the two above
#
# Enhanced Features:
#   -g flag to enable gzip compression for files marked with gzip flag in JSON

import os
import sys
import struct
import io
import ctypes
import gzip
from ctypes import *    # crc16


from utility import *
from ipmiclasses import *
from ipmipack import *
from jsonparser import *
from dmtfpack import *

#################################################################################

# constants

#tool version
FRU_PACKING_TOOL_VERSION = 1

#globals
g_binFileOut="fru.bin"        # -o FILE CLI option:  Output binary FRU file
g_endian_type = "<"           # All FRU data numbers must be LITTLE endian format
g_isVerbose = False
g_enableGzip = False          # -g CLI option: Enable gzip compression



#################################################################################

IPMI_IMAGE_SIZE_MINIMUM = 256

# Build the ipmi image from input json file
def build_ipmi_image(ipmi_input_file, dmtfOemRecordObj = None, verbose=False):
    """
    Builds an IPMI FRU image from the provided input file and optional OEM record object.
    This function parses the IPMI JSON input file, constructs the various FRU areas (chassis, board, product),
    and packs any available multi-record areas (HPM, peripheral, OEM) into a binary image buffer. The resulting
    image buffer can be used for programming FRU devices or further processing.
    Args:
        ipmi_input_file (str): Path to the IPMI JSON input file containing FRU data.
        dmtfOemRecordObj (object, optional): An object representing the DMTF OEM record to be included in the image.
        verbose (bool, optional): If True, prints detailed debug information during image construction.
    Returns:
        tuple:
            rc (int): Return code indicating success (0) or error (non-zero).
            imgBuf (ctypes.c_char_Array): The constructed IPMI FRU image buffer, or None if an error occurred.
    Notes:
        - The function expects the input file to contain valid IPMI FRU records.
        - Only one of HPM or peripheral multi-record areas will be packed, depending on availability.
        - The OEM record, if provided, is packed at the end of the multi-record area.
        - The function prints debug information if verbose is enabled.
    """
    rc = 0
    oemRecordPacked = None
    hpmMultiRecordPacked = None
    chassisInfoPacked = None
    boardInfoPacked = None
    productInfoPacked = None
    peripheralMultiRecordPacked = None

    if verbose: 
        print("Creating IPMI FRU")

    # This example only has the HPM multirecord or peripheral multirecord 
    # plus the oem multirecord at the end of the ipmi fru multirecord area
    # multiRecordArea = []

    # Parse the ipmi json file
    rc, ipmiObj = parse_ipmi_json_file(ipmi_input_file, verbose)
    if rc != 0:
        print(f"PARSING IPMI ERROR {rc}")
        return rc, None        

    # Internal use area - currently not building

    # Build chassis info area byte packed format
    if ipmiObj.chassisRecord:
        chassisInfoPacked = pack_ipmi_chassis_area(ipmiObj, verbose)

    #build board info area byte packed format
    if ipmiObj.boardRecord:
        boardInfoPacked = pack_ipmi_board_area(ipmiObj, verbose)

    # Build product info area byte packed format
    if ipmiObj.productRecord:
        productInfoPacked = pack_ipmi_product_area(ipmiObj, verbose)

    # Build the HPM multirecord if it exists in the input file

    if ipmiObj.hpmRecord:
        if verbose: 
            print("Creating HPM MULTIRECORD")        
        rc, hpmMultiRecordPacked = build_hpm_multirecord(ipmiObj.hpmRecord, verbose)
       
        print(f"Creating HPM MULTIRECORD RC={rc}")   

        if rc != 0:
            return rc, None
    
    elif ipmiObj.peripheralMultiRecord:
        if verbose: 
            print("Creating PERIPHERAL MULTIRECORD")        
        rc, peripheralMultiRecordPacked = build_peripheral_multirecord(ipmiObj.peripheralMultiRecord, verbose)        
        print(f"Creating PERIPHERAL MULTIRECORD RC={rc}")   
        
        if rc != 0:        
            return rc, None
    else:
        if verbose: 
            print("NO HPM OR PERIPHERAL MULTIRECORD!")             


    # Build multirecord area if OEM record exists
    if dmtfOemRecordObj:
        print("Creating DMTF OEM MR")
        dmtfOemRecordObj.dmtfFruOffset = IPMI_IMAGE_SIZE_MINIMUM 

        # Using oemRecord, now create the multirecord entry
        oemRecordPacked = pack_oem_record(dmtfOemRecordObj, verbose)

        if verbose:        
            hexdump("OEM Record Bytes:",oemRecordPacked,0,len(oemRecordPacked), verbose)

    if verbose:
        if chassisInfoPacked:        
            print(f"Chassis Record Bytes: {len(chassisInfoPacked)}")
            hexdump("Chassis Record Bytes: ",chassisInfoPacked,0,len(chassisInfoPacked), verbose)

        if boardInfoPacked:     
            print(f"Board Record Bytes: {len(boardInfoPacked)}")
            hexdump("Board Record Bytes:",boardInfoPacked,0,len(boardInfoPacked), verbose)

        if productInfoPacked:   
            print(f"Product Record Bytes: {len(productInfoPacked)}")
            hexdump("Product Record Bytes:",productInfoPacked,0,len(productInfoPacked), verbose)

        if hpmMultiRecordPacked:
            print(f"HPM Multi-Record Bytes: {len(hpmMultiRecordPacked)}")
            hexdump("HPM Multi-Record Bytes:",hpmMultiRecordPacked,0,len(hpmMultiRecordPacked), verbose)

        if peripheralMultiRecordPacked:
            print(f"Peripheral Multi-Record Bytes: {len(peripheralMultiRecordPacked)}")
            hexdump("Peripheral Multi-Record Bytes:",peripheralMultiRecordPacked,0,len(peripheralMultiRecordPacked), verbose)

    # Calculate offsets
    intUseOffset = 0  # no internal use area for this POC
    offset = int(COMMON_HEADER_SIZE_MINIMUM) + intUseOffset

    if chassisInfoPacked != None: 
        chassisInfoOffset = offset
        offset = chassisInfoOffset + len(chassisInfoPacked)
    else:
        chassisInfoOffset = 0

    if boardInfoPacked != None: 
        boardAreaOffset = offset
        offset = boardAreaOffset + len(boardInfoPacked)          
    else:
        boardAreaOffset = 0

    if productInfoPacked != None: 
        productAreaOffset = offset
        offset = productAreaOffset + len(productInfoPacked)        
    else:    
        productAreaOffset = 0

    multiRecordAreaOffset = offset

    # Build common header using buffers
    header = pack_ipmi_header(intUseOffset,chassisInfoOffset,boardAreaOffset,productAreaOffset,multiRecordAreaOffset)


    if verbose:
        print(f"Common Header Bytes: {len(header)}")
        hexdump("Common Header Bytes:",header,0,len(header), verbose)

    imgBuf = ctypes.create_string_buffer(IPMI_IMAGE_SIZE_MINIMUM)

    # Copy header into buffer
    imgBuf[:len(header)] = header

    if chassisInfoPacked != None: 
        chassisLength= len(chassisInfoPacked)
        print(f"Chassis Info Length: {chassisLength}")
        imgBuf[chassisInfoOffset:chassisInfoOffset + chassisLength] = chassisInfoPacked

    if boardInfoPacked != None:    
        boardLength= len(boardInfoPacked) 
        print(f"Board Info Length: {boardLength}")      
        print(f"Board Info Offset: {boardAreaOffset}")              
        imgBuf[boardAreaOffset:boardAreaOffset + boardLength] = boardInfoPacked

    if productInfoPacked != None:        
        productLength= len(productInfoPacked)    
        print(f"Product Info Length: {productLength}")                      
        imgBuf[productAreaOffset:productAreaOffset + productLength] = productInfoPacked
    
    multiRecordNextOffset = multiRecordAreaOffset

    # If we have an HPM multirecord then it should be packed next
    if hpmMultiRecordPacked:
        imgBuf[multiRecordNextOffset:multiRecordNextOffset + len(hpmMultiRecordPacked)] = hpmMultiRecordPacked
        multiRecordNextOffset += len(hpmMultiRecordPacked)
    elif peripheralMultiRecordPacked:
        imgBuf[multiRecordNextOffset:multiRecordNextOffset + len(peripheralMultiRecordPacked)] = peripheralMultiRecordPacked
        multiRecordNextOffset += len(peripheralMultiRecordPacked)

    # If we have an OEM record then we should pack it in the image buffer at the start of the multirecord area
    if oemRecordPacked:
        imgBuf[multiRecordNextOffset:multiRecordNextOffset + len(oemRecordPacked)] = oemRecordPacked

    return rc, imgBuf


###################################################################################

# Enhanced function to parse DMTF JSON input file with gzip support feature
def parse_dmtf_json_with_gzip(json_input_file, enable_gzip=False, verbose=False):
    """
    Parses a DMTF-style JSON file containing file metadata and returns lists of filenames, FdtEntry objects, 
    and compression flags indicating which files should be gzipped.
    Args:
        json_input_file (str): Path to the JSON input file containing file metadata.
        enable_gzip (bool, optional): If True, enables gzip compression for files marked as such in the JSON. Defaults to False.
        verbose (bool, optional): If True, prints detailed debug information during parsing. Defaults to False.
    Returns:
        tuple:
            - file_list (list of str): List of filenames extracted from the JSON.
            - fdt_list (list of FdtEntry): List of FdtEntry objects constructed from the JSON metadata.
            - compression_flags (list of bool): List indicating whether each file should be gzipped.
    Raises:
        SystemExit: If required fields such as "Filename" or "FormatIdentifier" are missing or empty in any file entry.
    Notes:
        - Assumes the JSON file contains a "Files" key with a list of file entries.
        - If "FormatVersion" is missing, defaults to 0.
        - Compression flags are set based on the "Flags" field and the enable_gzip parameter.
    """

    fdt_list = []
    file_list = []
    compression_flags = []  # Track which files should be compressed

    # Parse JSON from a file
    with open(json_input_file, "r") as file:
        python_dict_from_file = json.load(file)

    if verbose:  
        print(python_dict_from_file)

    for file_entry in python_dict_from_file['Files']:

        # Filename must be there and not empty
        if file_entry["Filename"]:
            
            if verbose: 
                print(file_entry["Filename"])

            file_list.append(file_entry["Filename"])
        else:
            print(f"Filename must be present - exiting!")
            sys.exit(1)            

        # Format identifier must be present
        if file_entry["FormatIdentifier"]:        
            fid = file_entry["FormatIdentifier"]
        else:
            print(f"Format ID must be present - exiting!")
            sys.exit(1)    

        # If version is not present then it is assumed to be 0
        ver = 0
        if file_entry["FormatVersion"]:
            ver = file_entry["FormatVersion"]

        resident = False
        dynamic =  False
        checksum = False
        compression = "none"
        should_gzip = False

        # Make sure flags are present in the json
        if file_entry["Flags"]:
            resident = file_entry["Flags"]["Resident"]
            dynamic = file_entry["Flags"]["Dynamic"]
            checksum = file_entry["Flags"]["ChecksumPresent"]
            compression = file_entry["Flags"]["Compression"]

            # Check if this file should be gzipped
            if enable_gzip and compression == "gzip":
                should_gzip = True
                if verbose:
                    print(f"File {file_entry['Filename']} will be gzipped")

        compression_flags.append(should_gzip)

        context = file_entry["Context"]

        # Pack the flags
        flags = 0

        if checksum:
            flags |= 0b0100

        if dynamic:
            flags |= 0b10000

        if resident:
           flags |= 0b100000

        # Only set compression flags if gzip is enabled and this file should be compressed
        if should_gzip:
            flags |= 0b0010  # gzip flag
        elif enable_gzip and compression == "messagepack":
            flags |= 0b0001
        elif enable_gzip and compression == "another":
            flags |= 0b0011

        fdt = FdtEntry(fid,ver,resident,0,flags,context)
        
        if verbose:        
            print(fdt)

        fdt_list.append(fdt)

    if verbose:    
        print(f"File List: {file_list}")
        print(f"Compression Flags: {compression_flags}")

    return file_list, fdt_list, compression_flags

# Creates a DMTF image with gzip support feature
def build_dmtf_image(dmtf_input_file, enable_gzip=False, verbose=False):
    """
    Builds a DMTF-compliant FRU image from a given input file describing files to be packed.
    This function parses a DMTF JSON input file, optionally compresses files using gzip,
    constructs a file descriptor table (FDT), and assembles a binary buffer containing the FRU header,
    FDT entries, and file data (compressed or original). The resulting buffer can be written to disk
    as a FRU image.
    Args:
        dmtf_input_file (str): Path to the DMTF JSON input file describing files and metadata.
        enable_gzip (bool, optional): If True, compress files marked for compression using gzip. Defaults to False.
        verbose (bool, optional): If True, prints detailed progress and debug information. Defaults to False.
    Returns:
        ctypes.c_char_Array: A binary buffer containing the packed FRU image.
    Raises:
        SystemExit: If any input file listed in the JSON is not found on disk.
    """
    
    file_list, fdt_list, compression_flags = parse_dmtf_json_with_gzip(dmtf_input_file, enable_gzip, verbose)

    # Print the list of packed data
    if verbose:
        print(file_list)

    file_count = len(file_list)

    if verbose: 
        print(f"Number of files {file_count}")
        print(f"FDT Count {len(fdt_list)}")

    # Create FRU header
    header = struct.pack(DMTF_FRU_HEADER_FORMAT, DMTF_FRU_IDENTIFIER, DMTF_FRU_VERSION, file_count,0)

    # Calculate total file size (including compressed files)
    totalfilesize = 0
    processed_files = []
    
    for i, input_file in enumerate(file_list):
        if not os.path.isfile(input_file):
            print(f"Error: {input_file} is not a valid file.")
            sys.exit(1)
            
        original_size = os.path.getsize(input_file)
        
        if compression_flags[i]:  # Should gzip this file
            # Read and compress the file
            with open(input_file, 'rb') as f:
                file_data = f.read()
            
            compressed_data = gzip.compress(file_data)
            processed_files.append(compressed_data)
            file_size = len(compressed_data)
            
            if verbose:
                print(f"Compressed {input_file}: {original_size} -> {file_size} bytes ({100*file_size/original_size:.1f}%)")
        else:
            # Keep original file
            processed_files.append(None)  # Will read later
            file_size = original_size
            
        totalfilesize += file_size
        # Update FDT entry with actual file size
        fdt_list[i].size = file_size

    if verbose: 
        print(f"Total File Block Size {totalfilesize}")

    # Rebuild file descriptor table with updated sizes
    file_descriptor_table = build_fdt(file_list, fdt_list, False)

    if verbose:
        print(f"FDT Size {len(file_descriptor_table) * FDT_ENTRY_SIZE}")
        print(file_descriptor_table)

    binBuf = ctypes.create_string_buffer(len(header) + FDT_ENTRY_SIZE * len(file_descriptor_table) + totalfilesize)

    # Copy header, file_descriptor_table, and files into binary buffer

    binBuf[0 : len(header)] = header

    offset = len(header) 
    for fdtEntry in file_descriptor_table:
        binBuf[ offset : offset + FDT_ENTRY_SIZE] = fdtEntry
        offset +=FDT_ENTRY_SIZE

    # Read in files and copy to buffer
    for i, input_file in enumerate(file_list):
        if verbose: 
            print(f"Adding File: {input_file}")

        if processed_files[i] is not None:
            # Use pre-compressed data
            file_data = processed_files[i]
            file_size = len(file_data)
            
            buffer = io.BytesIO(file_data)
            binBuf[offset : offset + file_size] = buffer.getbuffer()
            offset += file_size
            
            if verbose:
                print(f"Added compressed {input_file} image.")
        else:
            # Read original file
            file_size = os.path.getsize(input_file)
            
            # Create a buffer in memory (we use BytesIO)
            with open(input_file, 'rb') as file: 
                buffer = io.BytesIO(file.read())
                binBuf[offset : offset + file_size] = buffer.getbuffer()  
                offset += file_size    

            if verbose:
                print(f"Added {input_file} image.")

    return binBuf

# Creates the full image
# Packs the set of FRU file entries in the table
# Appends the file data and takes in the input parameters and writes the binary file and returns result code
def create_fru_image(dmtf_input_file, ipmi_input_file, output_file, enable_gzip=False, verbose=False):
    """
    Creates a combined FRU (Field Replaceable Unit) image from DMTF and IPMI input files and writes it to an output file.
    This function builds the DMTF FRU image (if provided), then builds the IPMI FRU image, combines both buffers,
    and writes the resulting image to the specified output file. Optionally, the DMTF image can be gzip-compressed.
    Verbose output can be enabled for detailed logging.
    Args:
        dmtf_input_file (str): Path to the DMTF FRU input file. If None or empty, DMTF image is not included.
        ipmi_input_file (str): Path to the IPMI FRU input file.
        output_file (str): Path to the output file where the combined FRU image will be written.
        enable_gzip (bool, optional): If True, gzip-compress the DMTF FRU image. Defaults to False.
        verbose (bool, optional): If True, print detailed debug information. Defaults to False.
    Returns:
        int: Return code indicating success (0) or failure (non-zero).
            0 - Success
            1 - Error building FRU image or writing output file
    Raises:
        SystemExit: If an error occurs while writing the output file.
    """
    dmtfBuf = []
    ipmiBuf = None
    rc = False

    print("Creating FRU Image...")

    # Determine schema directory relative to this script
    schema_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")

    # Validate DMTF input file against schema if provided
    if dmtf_input_file:
        dmtf_schema = os.path.join(schema_dir, "fru-tool-input-v0_1_0.json")
        valid, msg = validate_json_with_schema(dmtf_input_file, dmtf_schema)
        if not valid:
            print(f"Schema validation error: {msg}")
            return 1
        if verbose:
            print(msg)

    # Validate IPMI input file against schema
    if ipmi_input_file:
        ipmi_schema = os.path.join(schema_dir, "fru-tool-ipmi-v0_1_0.json")
        valid, msg = validate_json_with_schema(ipmi_input_file, ipmi_schema)
        if not valid:
            print(f"Schema validation error: {msg}")
            return 1
        if verbose:
            print(msg)

    # Create the DMTF FRU image if it is present
    if dmtf_input_file:
        dmtfBuf = build_dmtf_image(dmtf_input_file, enable_gzip, verbose)
        dmtfOemRecordObj = DmtfOemRecord()  #just use defaults, and do not know offset for DMTF FRU until IPMI FRU is built

        hexdump("DMTF FRU Buffer:",dmtfBuf,0,len(dmtfBuf), verbose)

    # Create the IPMI FRU image
    rc, ipmiBuf = build_ipmi_image(ipmi_input_file, dmtfOemRecordObj, verbose)

    if rc != 0:
        print(f"Error building FRU: {rc}")
        return rc

    if ipmiBuf == None:
        rc = 1
        print(f"Error building FRU: {rc}")
        return rc

    if len(ipmiBuf) == 0:
        rc = 1
        print(f"Error building FRU: {rc}")
        return rc        

    # Dumps the IPMI FRU buffer
    hexdump("IPMI FRU Buffer:",ipmiBuf,0,len(ipmiBuf), verbose)

    # Writes the file given the two buffers
    imageBuf = ctypes.create_string_buffer(len(ipmiBuf) + len(dmtfBuf))

    imageBuf[0 : len(ipmiBuf) ] = ipmiBuf

    if dmtfBuf:
        imageBuf[len(ipmiBuf) : len(ipmiBuf) + len(dmtfBuf)] = dmtfBuf

    # Dumps the image buffer
    hexdump("Image Buffer:",imageBuf,0,len(imageBuf), verbose)

    # Then writes out the output file
    try:
        with open(output_file, "wb") as f_out:
            
            if verbose: 
                print(f"\nWriting Image File: {output_file}")

            f_out.write(imageBuf)    
        if verbose:
            print(f"Full FRU image created: {output_file}")

    except Exception as e:
        print(f"Error writing FRU archive: {e}")
        sys.exit(1)

    return rc



# Main CLI entry point for the FRU packing tool
# Parses command line arguments and calls the create_fru_image function
def main():
    """
    Main entry point for the Enhanced IPMI and DMTF FRU Image Creation Tool with Gzip Support.
    Parses command-line arguments to specify input and output files, verbosity, and gzip compression options.
    Invokes the FRU image creation process using the provided JSON files for DMTF and IPMI FRU sections.
    Command-line arguments:
        -o, --output   : Name of the output FRU image file (required).
        -f, --file     : Name of the JSON-formatted input file for the DMTF FRU section (required).
        -i, --ipmi     : Name of the JSON-formatted input file for the IPMI FRU section (required).
        -v, --verbose  : Enable verbose output (optional).
        -g, --gzip     : Enable gzip compression for files marked with the gzip flag in JSON (optional).
    Prints the tool version, status messages, and error information.
    """

    import argparse
    global g_isVerbose

    toolversion = FRU_PACKING_TOOL_VERSION
    print("")
    print(f"Enhanced IPMI and DMTF FRU Image Creation Tool with Gzip Support Version {toolversion}")

    parser = argparse.ArgumentParser(description="Enhanced IPMI / DMTF FRU Creation with Gzip Support")
    
    parser.add_argument("-o", "--output", required=True,  help="name of FRU files image")
    parser.add_argument("-f", "--file", required=True,  help="name of json formated input file for DMTF FRU section")
    parser.add_argument("-i", "--ipmi", required=True,  help="name of json formated input file for IPMI FRU section")

    parser.add_argument("-v", "--verbose", action="store_true", required=False,  help="verbose output")
    parser.add_argument("-g", "--gzip", action="store_true", required=False,  help="enable gzip compression for files marked with gzip flag in JSON")

    args = parser.parse_args()

    g_isVerbose = args.verbose

    rc = create_fru_image(args.file, args.ipmi, args.output, args.gzip, g_isVerbose)
    if rc:
        print(f"Error building FRU image! rc={rc}")
    else:
        print("FRU image creation completed successfully.")


if __name__ == "__main__":
    main()
