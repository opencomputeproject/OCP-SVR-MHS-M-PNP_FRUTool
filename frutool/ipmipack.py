# SPDX-FileCopyrightText: 2025 Hewlett Packard Enterprise Development LP
# SPDX-License-Identifier: MIT

# IPMI Byte Packing Functions
# This module contains functions to pack various IPMI records into byte buffers.

import ctypes
from ctypes import *    # crc16
import datetime

from utility import *
from ipmiclasses import *


#############################################################################
# IPMI record byte packing functions
#

CHASSIS_AREA_SIZE_MINIMUM = 7
DEFAULT_FORMAT_VERSION = 1

# Create IPMI chassis area info record.
# See IPMI FRU specification for details.
def pack_ipmi_chassis_area(ipmiObj, verbose=False):
    """
    Packs the IPMI chassis area information into a binary buffer according to the IPMI FRU specification.
    Args:
        ipmiObj: An object containing chassis information, expected to have a 'chassisRecord' attribute with
                 'formatVersion', 'chassisType', 'chassisPartNumber', and 'chassisSerialNumber' fields.
        verbose (bool, optional): If True, prints debug information about the packing process. Defaults to False.
    Returns:
        ctypes.c_char_Array: A binary buffer containing the packed chassis area data, including padding and checksum.
    Notes:
        - The buffer is padded to ensure the chassis area is aligned to an 8-byte boundary.
        - The function computes and inserts the correct area size and checksum.
        - The packing format follows the IPMI FRU chassis area specification.
    """

    chassisObj = ipmiObj.chassisRecord

    fmtVer = chassisObj.formatVersion
    ct = chassisObj.chassisType

    if verbose:
        print(f"Chassis Area: Format Ver: {fmtVer}")
        print(f"Chassis Area: Chassis Type: { ct}")
    
    chassis_pn = chassisObj.chassisPartNumber
    chassis_sn = chassisObj.chassisSerialNumber

    cpnSize = len(chassis_pn)
    csnSize = len(chassis_sn)
    
    #calculate size of buffer based on lengths needed
    #chassis info area format   1B
    #chassis info area length   1B
    #chassis type enum          1B
    #chassis pn type and length 1B
    #chassis part number string             1B * CPNSIZE
    #chassis serial number type and length  1B
    #chasis serial number string            1B * CSNSIZE
    #custom chassis info fields - NOT IN THIS POC
    #TYPE/LENGTH END BYTE ENCODING          1B
    #PADDING SPACE                          Variable - padding to make chassis area on even boundary
    #checksum                               1B
    sizeNoPadding = CHASSIS_AREA_SIZE_MINIMUM + cpnSize + csnSize

    # Determine if extra padding is needed - put chassis area on 8 byte boundaries
    # to make it easier to debug if everything is aligned to 8 byte sections
    # and size of chassis info area length must be multiples of 8 bytes
    remainder = sizeNoPadding % 8
    padding = 0
    if remainder:
        padding = 8 - remainder

    binBuf = ctypes.create_string_buffer(sizeNoPadding + padding)

    areaSz = 0
    off=0
    off += appendByteBuf(binBuf, DEFAULT_FORMAT_VERSION, off, "uchar")
    off += appendByteBuf(binBuf, int(areaSz/8), off, "uchar")
    off += appendByteBuf(binBuf, ct, off, "uchar") # chassis type from parsed JSON

    off += appendByteBuf(binBuf, 0xC0 | cpnSize, off, "uchar") # PartNum type / size
    off += appendByteBuf(binBuf, chassis_pn, off, "str")

    off += appendByteBuf(binBuf, 0xC0 | csnSize, off, "uchar") # type/areaSz
    off += appendByteBuf(binBuf, chassis_sn, off, "str")


    off += appendByteBuf(binBuf, 0xC1, off, "uchar")#EndOfRecord
    off += 1 # checksum
    off += getPadBytes(off)
    areaSz = off
    
    # Add new size into location byte 1
    appendByteBuf(binBuf, int(areaSz/8), 1, "uchar")
    
    cs = computeZeroChecksum(binBuf.raw, 0, areaSz-1)
    appendByteBuf(binBuf, cs, areaSz-1, "uchar")


    return binBuf

##############################################################

PRODUCT_AREA_SIZE_MINIMUM = 12

# Create IPMI product area info record.
# See IPMI FRU specification for details.
def pack_ipmi_product_area(ipmiObj, verbose = False):
    """
    Packs the IPMI FRU Product Area fields into a binary buffer according to the IPMI FRU specification.
    Args:
        ipmiObj: An object containing the FRU product record information. Must have a `productRecord` attribute
            with the following fields:
                - formatVersion: Format version of the product area.
                - languageCode: Language code for the product area.
                - mfgName: Manufacturer name (string).
                - productName: Product name (string).
                - productNum: Product part number (string).
                - productVersion: Product version (string).
                - productSerialNum: Product serial number (string).
                - assetTag: Asset tag (string).
                - fruFileID: FRU file ID (string).
        verbose (bool, optional): If True, prints debug information about the packing process. Defaults to False.
    Returns:
        ctypes.c_char_Array: A ctypes string buffer containing the packed binary representation of the product area.
    Notes:
        - The function calculates the required padding to align the area size to an 8-byte boundary.
        - The function appends each product field with its type/size byte and value.
        - The function computes and appends a zero checksum for the product area.
        - The function assumes the existence of helper functions: appendByteBuf, getPadBytes, and computeZeroChecksum.
    """

    # Get the product area info from the ipmiObj object.
    # This object should have a productRecord attribute with the necessary fields.
    productObj = ipmiObj.productRecord

    fmtVer = productObj.formatVersion
    languageCode = productObj.languageCode

    if verbose:
        print(f"Product Area: Format Ver: {fmtVer}")
        print(f"Product Area: Language Code: { languageCode}")

    productMfg = productObj.mfgName
    productName = productObj.productName
    productPartNum = productObj.productNum
    productVersion = productObj.productVersion    
    productSerial = productObj.productSerialNum
    productAssetTag = productObj.assetTag
    fruFileID  = productObj.fruFileID

    productMfgSize = len(productMfg)
    productNameSize = len(productName)
    productPartNumSize = len(productPartNum)
    productVersionSize = len(productVersion)      
    productSerialSize = len(productSerial)
    productAssetTagSize = len(productAssetTag)    
    fruFileIDSize = len(fruFileID)    

    sizeNoPadding = PRODUCT_AREA_SIZE_MINIMUM + productMfgSize + productNameSize + \
        productPartNumSize + productSerialSize + productVersionSize + productAssetTagSize + fruFileIDSize

    remainder = sizeNoPadding % 8
    padding = 0
    if remainder:
        padding = 8 - remainder

    binBuf = ctypes.create_string_buffer(sizeNoPadding + padding)

    offStart = 0
    areaSz = 0
    off=0

    off += appendByteBuf(binBuf, 0x01, off, "uchar")
    off += appendByteBuf(binBuf, int(areaSz/8), off, "uchar")
    off += appendByteBuf(binBuf, 0x19, off, "uchar") #lang code=English
    off += appendByteBuf(binBuf, 0xC0 | len(productMfg), off, "uchar") # Type/Sz
    off += appendByteBuf(binBuf, productMfg, off, "str")
    off += appendByteBuf(binBuf, 0xC0 | len(productName), off, "uchar") # Type/Sz
    off += appendByteBuf(binBuf, productName, off, "str")
    off += appendByteBuf(binBuf, 0xC0 | len(productPartNum), off, "uchar")# Type/Sz
    off += appendByteBuf(binBuf, productPartNum, off, "str")
    off += appendByteBuf(binBuf, 0xC0 | len(productVersion), off, "uchar")
    off += appendByteBuf(binBuf, productVersion, off, "str")
    off += appendByteBuf(binBuf, 0xC0 | len(productSerial), off, "uchar")# Type/Sz
    off += appendByteBuf(binBuf, productSerial, off, "str")

    off += appendByteBuf(binBuf, 0xC0 | len(productAssetTag), off, "uchar")# Type/Sz
    off += appendByteBuf(binBuf, productAssetTag, off, "str")

    off += appendByteBuf(binBuf, 0xC0 | len(fruFileID), off, "uchar")# Type/Sz
    off += appendByteBuf(binBuf, fruFileID, off, "str")

    off += appendByteBuf(binBuf, 0xC1, off, "uchar")#EndOfRecord
    off += 1 # checksum

    off += getPadBytes(off)
    areaSz = off-offStart
    appendByteBuf(binBuf, int(areaSz/8), offStart+1, "uchar")
    cs = computeZeroChecksum(binBuf.raw, offStart, offStart+areaSz-1)
    appendByteBuf(binBuf, cs, offStart+areaSz-1, "uchar")    

    return binBuf

##############################################################

BOARD_AREA_SIZE_MINIMUM = 13

# Create IPMI multi-record header.
# See IPMI FRU specification for details.
def pack_ipmi_board_area(ipmiObj, verbose = False):
    """
    Packs the IPMI board area information into a binary buffer according to the IPMI FRU specification.
    Args:
        ipmiObj: An object containing board record information, expected to have attributes:
            - boardRecord: The board record object with the following fields:
                - formatVersion (int): The format version of the board area.
                - languageCode (int): The language code for the board area.
                - mfgTime (str): Manufacturing time in ISO 8601 format (YYYY-MM-DDThh:mm:ss+00:00).
                - boardMfg (str): Board manufacturer string.
                - boardName (str): Board name string.
                - boardSerial (str): Board serial number string.
                - boardPartNum (str): Board part number string.
                - fruFileID (str): FRU file ID string.
        verbose (bool, optional): If True, prints debug information during packing. Defaults to False.
    Returns:
        ctypes.c_char_Array: A ctypes string buffer containing the packed binary board area.
    Notes:
        - The function calculates the required buffer size, applies padding to align to 8 bytes,
            and computes the checksum for the board area.
        - The packed buffer can be used for IPMI FRU data storage or transmission.
    """

    boardObj = ipmiObj.boardRecord

    fmtVer = boardObj.formatVersion
    languageCode = boardObj.languageCode
    mfgTime = boardObj.mfgTime

    if verbose:
        print(f"Board Area: Format Ver: {fmtVer}")
        print(f"Board Area: Language Code: { languageCode}")
        print(f"Board Area: Mfg Time: { mfgTime}")

    # Timestamp in YYYY-MM-DDThh:mm:ss+0000 format
    factTimeStamp = 0
    if mfgTime:
        date_format = datetime.datetime.strptime(mfgTime,"%Y-%m-%dT%H:%M:%S+00:00")
        factTimeStamp = int(datetime.datetime.timestamp(date_format))

    if verbose:    
        print(f"Linux Timestamp: {factTimeStamp}")

    boardMfg = boardObj.boardMfg
    boardName = boardObj.boardName
    boardSerial = boardObj.boardSerial
    boardPartNum = boardObj.boardPartNum
    fruFileID  = boardObj.fruFileID



    boardMfgSize = len(boardMfg)
    boardNameSize = len(boardName)
    boardSerialSize = len(boardSerial)
    boardPartNumSize = len(boardPartNum)    
    fruFileIDSize = len(fruFileID)    

    sizeNoPadding = BOARD_AREA_SIZE_MINIMUM + boardMfgSize + boardNameSize + boardSerialSize +boardPartNumSize+fruFileIDSize

    remainder = sizeNoPadding % 8
    padding = 0
    if remainder:
        padding = 8 - remainder

    binBuf = ctypes.create_string_buffer(sizeNoPadding + padding)

    offStart = 0
    areaSz = 0
    off=0
    off += appendByteBuf(binBuf, DEFAULT_FORMAT_VERSION, off, "uchar")

    off += appendByteBuf(binBuf, int(areaSz/8), off, "uchar")
    off += appendByteBuf(binBuf, 0x19, off, "uchar") #lang code=English

    off += appendByteBuf(binBuf, (factTimeStamp&0x0000FF), off, "uchar")
    off += appendByteBuf(binBuf, (factTimeStamp&0x00FF00)>>8, off, "uchar")
    off += appendByteBuf(binBuf, (factTimeStamp&0xFF0000)>>16, off, "uchar")

    off += appendByteBuf(binBuf, 0xC0 | len(boardMfg), off, "uchar") # Type/Sz
    off += appendByteBuf(binBuf, boardMfg, off, "str")
    off += appendByteBuf(binBuf, 0xC0 | len(boardName), off, "uchar") # Type/Sz
    off += appendByteBuf(binBuf, boardName, off, "str")

    off += appendByteBuf(binBuf, 0xC0 | len(boardSerial), off, "uchar")# Type/Sz
    off += appendByteBuf(binBuf, boardSerial, off, "str")

    off += appendByteBuf(binBuf, 0xC0 | len(boardPartNum), off, "uchar")# Type/Sz
    off += appendByteBuf(binBuf, boardPartNum, off, "str")    

    off += appendByteBuf(binBuf, 0xC0 | len(fruFileID), off, "uchar")# Type/Sz
    off += appendByteBuf(binBuf, fruFileID, off, "str")

    off += appendByteBuf(binBuf, 0xC1, off, "uchar")#EndOfRecord
    off += 1 # checksum
    off += getPadBytes(off)
    areaSz = off-offStart
    appendByteBuf(binBuf, int(areaSz/8), offStart+1, "uchar")
    cs = computeZeroChecksum(binBuf.raw, offStart, offStart+areaSz-1)
    appendByteBuf(binBuf, cs, offStart+areaSz-1, "uchar")
    
    return binBuf


##############################################################


DMTF_OEM_MULTIRECORD_SIZE_MINIMUM = 12
DMTF_OEM_MULTIRECORD_FIXED_LENGTH = 7
RECORD_CHECKSUM_OFFSET = 0x03
HEADER_CHECKSUM_OFFSET = 0x04
MFG_ID_OFFSET = 0x05
DMTF_FRU_LOCATION_OFFSET = 0x08

# Create DMTF OEM record formatted binary buffer. See DMTF FRU specification DSP0220 for details.
def pack_oem_record(dmtfOemRecordObj, verbose = False):
    """
    Packs a DMTF OEM record into a binary buffer according to the IPMI FRU specification.
    Args:
        dmtfOemRecordObj: An object containing the DMTF FRU offset and other necessary attributes.
        verbose (bool, optional): If True, prints debug information during packing. Defaults to False.
    Returns:
        ctypes.c_char_Array: A binary buffer containing the packed OEM record.
    Notes:
        - The function constructs the record header, sets manufacturer ID, FRU offset, and computes checksums.
        - Uses helper functions `appendByteBuf` and `computeZeroChecksum` for buffer manipulation and checksum calculation.
        - Assumes constants like `DMTF_OEM_MULTIRECORD_SIZE_MINIMUM`, `MFG_ID_OFFSET`, `DMTF_FRU_LOCATION_OFFSET`, 
          `RECORD_CHECKSUM_OFFSET`, `HEADER_CHECKSUM_OFFSET`, and `DMTF_OEM_MULTIRECORD_FIXED_LENGTH` are defined elsewhere.
    """
    # Get the DMTF OEM record object attributes.
    # This object should have a dmtfFruOffset attribute where the FRU offset is stored.
    dmtfFruOffset = dmtfOemRecordObj.dmtfFruOffset
    
    if verbose:       
        print(f"DMTF FRU OFFSET: {dmtfFruOffset}")

    binBuf = ctypes.create_string_buffer(DMTF_OEM_MULTIRECORD_SIZE_MINIMUM)

    offStart = 0
    off = 0
    off += appendByteBuf(binBuf, 0xC0, offStart, "uchar")
    off += appendByteBuf(binBuf, 0x82, off, "uchar")
    off += appendByteBuf(binBuf, DMTF_OEM_MULTIRECORD_FIXED_LENGTH, off, "uchar")

    appendByteBuf(binBuf, 0xB4, MFG_ID_OFFSET, "uchar")
    appendByteBuf(binBuf, 0x1A, MFG_ID_OFFSET+1, "uchar")
    appendByteBuf(binBuf, 0x00, MFG_ID_OFFSET+2, "uchar")

    appendByteBuf(binBuf, dmtfFruOffset, DMTF_FRU_LOCATION_OFFSET, "ulong")

    record_checksum = computeZeroChecksum(binBuf.raw, MFG_ID_OFFSET, DMTF_OEM_MULTIRECORD_SIZE_MINIMUM)

    # Put this in byte 3
    appendByteBuf(binBuf, record_checksum, RECORD_CHECKSUM_OFFSET, "uchar")

    # Header checksum
    cs = computeZeroChecksum(binBuf.raw, offStart, HEADER_CHECKSUM_OFFSET)
    appendByteBuf(binBuf, cs, HEADER_CHECKSUM_OFFSET, "uchar")

    return binBuf
    

#####################################################################################################

COMMON_HEADER_SIZE_MINIMUM = 8

# Create IPMI header. See IPMI FRU specification for details.
def pack_ipmi_header(internalUseOff, chassisOff, boardOff,productOff, mrecOff):

    """
    Packs the IPMI header into a binary buffer.
    This function constructs an IPMI header by appending various offsets (internal use, chassis, board, product, and MREC)
    to a binary buffer, calculates the checksum, and adds necessary padding bytes.
    Args:
        internalUseOff (int): Offset for the internal use area in bytes.
        chassisOff (int): Offset for the chassis area in bytes.
        boardOff (int): Offset for the board area in bytes.
        productOff (int): Offset for the product area in bytes.
        mrecOff (int): Offset for the MREC area in bytes.
    Returns:
        ctypes.c_char_Array: A binary buffer containing the packed IPMI header.
    """
    # Create a binary buffer with a minimum size for the common header.
    binBuf = ctypes.create_string_buffer(COMMON_HEADER_SIZE_MINIMUM)

    areaSz = 0
    off=0
    offStart = 0

    off += appendByteBuf(binBuf, 0x01, off, "uchar")
    off += appendByteBuf(binBuf, int(internalUseOff/8), off, "uchar")
    off += appendByteBuf(binBuf, int(chassisOff/8), off, "uchar")
    off += appendByteBuf(binBuf, int(boardOff/8), off, "uchar")
    off += appendByteBuf(binBuf, int(productOff/8), off, "uchar")
    off += appendByteBuf(binBuf, int(mrecOff/8), off, "uchar")
    off += 1 # checksum
    off += getPadBytes(off)
    areaSz = off-offStart
    cs = computeZeroChecksum(binBuf.raw, offStart, offStart+areaSz-2)
    appendByteBuf(binBuf, cs, offStart+areaSz-1, "uchar")


    return binBuf

##############################################################
# Constants for multi-record header
DEFAULT_RECORD_FORMAT_VERSION = 2
MULTIRECORD_HEADER_SIZE_MINIMUM  = 5
OEM_RECORD_FORMAT = 0xc0

# Create packed multirecord header. See IPMI FRU specification for details.
def build_multirecord_header(
        record_length=0,
        record_checksum=0,
        record_type=0,
        record_format_version=DEFAULT_RECORD_FORMAT_VERSION,
        end_of_list_flag=False
    ):
    """
    Constructs a multi-record header buffer for IPMI FRU data.
    Args:
        record_length (int, optional): Length of the record data. Defaults to 0.
        record_checksum (int, optional): Checksum value for the record data. Defaults to 0.
        record_type (int, optional): Type identifier for the record. Defaults to 0.
        record_format_version (int, optional): Format version of the record. Defaults to DEFAULT_RECORD_FORMAT_VERSION.
        end_of_list_flag (bool, optional): If True, sets the end-of-list flag in the header. Defaults to False.
    Returns:
        ctypes.c_char_Array: A ctypes string buffer containing the constructed multi-record header.
    Notes:
        - The header includes a checksum computed over its contents.
        - The end-of-list flag is set as bit 7 of the format version byte.
        - The buffer size is determined by MULTIRECORD_HEADER_SIZE_MINIMUM.
    """
    # Create a binary buffer with a minimum size for the multi-record header.
    binBuf = ctypes.create_string_buffer(MULTIRECORD_HEADER_SIZE_MINIMUM)

    offStart = 0
    rec_fmt = record_format_version
    rec_type = record_type

    if end_of_list_flag:  #flag is bit 7 in the spec
        rec_fmt = 0x80 | rec_fmt
 
    off += appendByteBuf(binBuf,rec_type, off, "uchar")
    off += appendByteBuf(binBuf, rec_fmt, off, "uchar")

    off += appendByteBuf(binBuf, record_length, off, "uchar")
    off += appendByteBuf(binBuf, record_checksum, off, "uchar")

    # Header checksum
    cs = computeZeroChecksum(binBuf.raw, offStart, offStart+MULTIRECORD_HEADER_SIZE_MINIMUM)
    appendByteBuf(binBuf, cs, offStart+MULTIRECORD_HEADER_SIZE_MINIMUM-1, "uchar")

    return binBuf

########################################################################################
# Constants for HPM multirecord

HPM_MULTIRECORD_OEM_RECORD_TYPE = 0xC1
HPM_MULTIRECORD_RECORD_FORMAT_VERSION = 0x01

HPM_MULTIRECORD_SIZE_MINIMUM = 0x14
OCP_HPM_MFG_ID_OFFSET = 5
OCP_HPM_OEM_RECORD_VERSION_OFFSET = 8
DC_SCI_REV_MAJOR_OFFSET = 9
DC_SCI_REV_MINOR_OFFSET = 10
DC_SCI_VERSION_OFFSET = 11

DC_LTPI_REVISION_MAJOR_OFFSET = 12
DC_LTPI_REVISION_MINOR_OFFSET = 13
DC_LTPI_VERSION_OFFSET = 14

DC_SCM_TYPE_OFFSET = 15
HPM_VENDOR_ID_OFFSET = 16
HPM_DEVICE_ID_OFFSET = 18

OCP_IANA_BYTE_0 = 0x7F
OCP_IANA_BYTE_1 = 0xA6
OCP_IANA_BYTE_2 = 0x00

OCP_HPM_OEM_RECORD_VERSION = 1

# Build the HPM multirecord assuming no implementation specific OEM section.
# See OCP SCM specification for details.
def build_hpm_multirecord(hpmMultirecordObj, verbose = False):
    """
    Builds an HPM (Hardware Platform Management) multirecord binary buffer from the provided object.
    This function extracts relevant fields from the `hpmMultirecordObj`, converts hex string IDs to integers,
    and populates a binary buffer according to the HPM multirecord format. It also computes and inserts
    checksums for both the record and the header.
    Args:
        hpmMultirecordObj: An object containing HPM multirecord fields such as revision numbers, version,
            vendor ID, device ID, and other required attributes.
        verbose (bool, optional): If True, prints debug information during processing. Defaults to False.
    Returns:
        tuple:
            - rc (bool or int): False if successful, or an error code if a conversion or format error occurs.
            - binBuf (ctypes.c_char_Array): The constructed binary buffer containing the HPM multirecord,
                or None if an error occurred.
    Raises:
        None explicitly, but returns error codes and None if input format errors are detected.
    Notes:
        - The function expects `hpmMultirecordObj` to have specific attributes required for HPM multirecord construction.
        - Uses helper functions such as `hexToNum`, `appendByteBuf`, and `computeZeroChecksum` for processing.
        - The buffer size and field offsets are determined by constants defined elsewhere in the codebase.
    """

    binBuf = ctypes.create_string_buffer(HPM_MULTIRECORD_SIZE_MINIMUM)


    sciRevisionMajor = hpmMultirecordObj.sciRevisionMajor   
    sciRevisionMinor = hpmMultirecordObj.sciRevisionMinor                

    sciVersion = hpmMultirecordObj.sciVersion     

    ltpiRevisionMajor = hpmMultirecordObj.ltpiRevisionMajor
    ltpiRevisionMinor = hpmMultirecordObj.ltpiRevisionMinor    
    ltpiVersion = hpmMultirecordObj.ltpiVersion  

    scmType = hpmMultirecordObj.scmType

    print(f"HPM VENDOR ID {hpmMultirecordObj.hpmVendorID}")

    rc, hpmVendorID = hexToNum(hpmMultirecordObj.hpmVendorID)  #this is a hex string - need to convert to integer
    if rc:  # failed so exit
        print(f"JSON HPM Vendor ID Format Error!  RC= {rc}")
        return rc, None

    print(f"HPM VENDOR ID NUMBER {hpmVendorID}")

    print(f"HPM DEVICE ID {hpmMultirecordObj.hpmDevID}")

    rc, hpmDevID = hexToNum(hpmMultirecordObj.hpmDevID)  #this is a hex string- need to convert to integer
    if rc:  # failed so exit
        printf("JSON HPM Device ID Format Error!")
        return rc, None

    print(f"HPM DEVICE ID NUMBER {hpmDevID}")

    off = 0
    offStart = off
    off += appendByteBuf(binBuf, HPM_MULTIRECORD_OEM_RECORD_TYPE, off, "uchar")  #type id = 0xC1 for HPM MR
    off += appendByteBuf(binBuf, HPM_MULTIRECORD_RECORD_FORMAT_VERSION, off, "uchar")  #This is format version

    off += appendByteBuf(binBuf, HPM_MULTIRECORD_SIZE_MINIMUM - MULTIRECORD_HEADER_SIZE_MINIMUM, off, "uchar")  #fixed record length


    appendByteBuf(binBuf, OCP_IANA_BYTE_0, OCP_HPM_MFG_ID_OFFSET, "uchar")
    appendByteBuf(binBuf, OCP_IANA_BYTE_1, OCP_HPM_MFG_ID_OFFSET+1, "uchar")
    appendByteBuf(binBuf, OCP_IANA_BYTE_2, OCP_HPM_MFG_ID_OFFSET+2, "uchar")

    appendByteBuf(binBuf, OCP_HPM_OEM_RECORD_VERSION, OCP_HPM_OEM_RECORD_VERSION_OFFSET, "uchar")

    appendByteBuf(binBuf, sciRevisionMajor, DC_SCI_REV_MAJOR_OFFSET, "uchar")  
    appendByteBuf(binBuf, sciRevisionMinor, DC_SCI_REV_MINOR_OFFSET, "uchar")  
    appendByteBuf(binBuf, sciVersion, DC_SCI_VERSION_OFFSET, "uchar")  

    appendByteBuf(binBuf, ltpiRevisionMajor, DC_LTPI_REVISION_MAJOR_OFFSET, "uchar")  
    appendByteBuf(binBuf, ltpiRevisionMinor, DC_LTPI_REVISION_MINOR_OFFSET, "uchar")  

    appendByteBuf(binBuf, ltpiVersion, DC_LTPI_VERSION_OFFSET, "uchar")  

    appendByteBuf(binBuf, scmType, DC_SCM_TYPE_OFFSET, "uchar")  

    appendByteBuf(binBuf, hpmVendorID, HPM_VENDOR_ID_OFFSET, "ushort")  

    appendByteBuf(binBuf, hpmDevID, HPM_DEVICE_ID_OFFSET, "ushort")  


    # Calculate record checksum
    record_checksum = computeZeroChecksum(binBuf.raw, OCP_HPM_MFG_ID_OFFSET, HPM_MULTIRECORD_SIZE_MINIMUM)

    # Put this in byte 3
    appendByteBuf(binBuf, record_checksum, RECORD_CHECKSUM_OFFSET, "uchar")


    # Calcuate header checksum
    cs = computeZeroChecksum(binBuf.raw, offStart, offStart + MULTIRECORD_HEADER_SIZE_MINIMUM - 1)
    appendByteBuf(binBuf, cs, offStart + MULTIRECORD_HEADER_SIZE_MINIMUM - 1, "uchar")

    return False, binBuf


###########################################################################################
# Constants for peripheral multirecord

PERIPHERAL_MULTIRECORD_OEM_RECORD_TYPE = 0xC3
PERIPHERAL_MULTIRECORD_RECORD_FORMAT_VERSION = 0x01

PERIPHERAL_MULTIRECORD_SIZE_MINIMUM = 11
OCP_PERIPHERAL_MFG_ID_OFFSET = 5
OCP_PERIPHERAL_OEM_RECORD_VERSION_OFFSET = 8
PERIPHERAL_DEVICE_CLASS_OFFSET = 9
PERIPHERAL_DEVICE_SUBCLASS_OFFSET = 10

OCP_PERIPHERAL_OEM_RECORD_VERSION = 1

# Build the peripheral multirecord assuming no implementation specific OEM section.
# See OCP M-PNP.FRU_DISCOVERY_BOOT specification for details.
def build_peripheral_multirecord(peripheralMultirecordObj, verbose = False):
    """
    Builds a binary buffer representing a peripheral multi-record structure for IPMI FRU data.
    This function constructs a multi-record binary buffer for a peripheral device, populating
    fields such as record type, format version, manufacturer ID, record version, device class,
    and subclass. It also computes and inserts both record and header checksums as required
    by the IPMI FRU specification.
    Args:
        peripheralMultirecordObj: An object containing peripheral device information, including
            `peripheralDeviceClass` and `peripheralDeviceSubClass` attributes.
        verbose (bool, optional): If True, enables verbose output for debugging purposes. Defaults to False.
    Returns:
        tuple:
            rc (bool): Status flag indicating success or failure of the build process.
            binBuf (ctypes.c_char_Array): The constructed binary buffer containing the multi-record data.
    """

    rc = False
    binBuf = ctypes.create_string_buffer(PERIPHERAL_MULTIRECORD_SIZE_MINIMUM)

    peripheralDeviceClass = peripheralMultirecordObj.peripheralDeviceClass
    peripheralDeviceSubClass = peripheralMultirecordObj.peripheralDeviceSubClass

    off = 0
    offStart = off
    off += appendByteBuf(binBuf, PERIPHERAL_MULTIRECORD_OEM_RECORD_TYPE, off, "uchar")  #type id = 0xC1 for HPM MR
    off += appendByteBuf(binBuf, PERIPHERAL_MULTIRECORD_RECORD_FORMAT_VERSION, off, "uchar")  #This is format version

    off += appendByteBuf(binBuf, PERIPHERAL_MULTIRECORD_SIZE_MINIMUM - MULTIRECORD_HEADER_SIZE_MINIMUM, off, "uchar")  #fixed record length


    appendByteBuf(binBuf, OCP_IANA_BYTE_0, OCP_PERIPHERAL_MFG_ID_OFFSET, "uchar")
    appendByteBuf(binBuf, OCP_IANA_BYTE_1, OCP_PERIPHERAL_MFG_ID_OFFSET+1, "uchar")
    appendByteBuf(binBuf, OCP_IANA_BYTE_2, OCP_PERIPHERAL_MFG_ID_OFFSET+2, "uchar")


    appendByteBuf(binBuf, OCP_PERIPHERAL_OEM_RECORD_VERSION, OCP_PERIPHERAL_OEM_RECORD_VERSION_OFFSET, "uchar")

    appendByteBuf(binBuf, peripheralDeviceClass, PERIPHERAL_DEVICE_CLASS_OFFSET, "uchar")  
    appendByteBuf(binBuf, peripheralDeviceSubClass, PERIPHERAL_DEVICE_SUBCLASS_OFFSET , "uchar")      

    #calculate record checksum
    record_checksum = computeZeroChecksum(binBuf.raw, OCP_PERIPHERAL_MFG_ID_OFFSET, PERIPHERAL_MULTIRECORD_SIZE_MINIMUM)

    #put this in byte 3
    appendByteBuf(binBuf, record_checksum, RECORD_CHECKSUM_OFFSET, "uchar")


    #calcuate header checksum
    cs = computeZeroChecksum(binBuf.raw, offStart, offStart + MULTIRECORD_HEADER_SIZE_MINIMUM - 1)
    appendByteBuf(binBuf, cs, offStart + MULTIRECORD_HEADER_SIZE_MINIMUM - 1, "uchar")

    return rc, binBuf
