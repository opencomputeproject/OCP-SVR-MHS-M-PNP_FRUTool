# SPDX-FileCopyrightText: 2025 Hewlett Packard Enterprise Development LP
# SPDX-License-Identifier: MIT

# JSON Parsing functions
# This module provides functions to parse JSON data related to IPMI FRU records.

import json
from ctypes import *    # crc16


from utility import *
from ipmiclasses import *
from ipmipack import *

#############################################################################
# json parsing functions
#

# Parse IPMI board info area.
# This function extracts board information from the provided IPMI JSON object.
# See IPMI FRU specification for details.
def parse_board_info_area(ipmiJson, verbose = False):
    """
    Parses the 'BoardInfo' section from an IPMI JSON object and returns an IpmiBoardRecord instance.
    Args:
        ipmiJson (dict): The JSON object containing IPMI data.
        verbose (bool, optional): If True, prints board information details. Defaults to False.
    Returns:
        IpmiBoardRecord or None: An instance of IpmiBoardRecord populated with board information if 'BoardInfo' exists,
        otherwise None.
    The function extracts the following fields from 'BoardInfo':
        - FormatVersion
        - LanguageCode
        - FactoryTimeStamp
        - Manufacturer
        - ProductName
        - SerialNumber
        - PartNumber
        - FRUFileID
    """

    boardAreaObj = None
    formatVersion = 0
    languageCode = 0
    mfgTime = ""
    boardMfg = ""
    boardName =""
    boardSerial =""
    boardPartNum = ""
    fruFileID= ""

    if ipmiJson.get('BoardInfo'):

        boardInfo  = ipmiJson["BoardInfo"]
        if verbose: 
            print("Board Info:")

        if boardInfo.get('FormatVersion'):  
            formatVersion = ipmiJson["BoardInfo"]["FormatVersion"]

        if boardInfo.get('LanguageCode'):  
            languageCode = ipmiJson["BoardInfo"]["LanguageCode"]

        if boardInfo.get('FactoryTimeStamp'):              
            mfgTime = ipmiJson["BoardInfo"]["FactoryTimeStamp"]

        if boardInfo.get('Manufacturer'):  
            boardMfg = ipmiJson["BoardInfo"]["Manufacturer"]

        if boardInfo.get('ProductName'):              
            boardName = ipmiJson["BoardInfo"]["ProductName"]

        if boardInfo.get('SerialNumber'):        
            boardSerial = ipmiJson["BoardInfo"]["SerialNumber"]

        if boardInfo.get('PartNumber'):                    
            boardPartNum = ipmiJson["BoardInfo"]["PartNumber"]

        if boardInfo.get('FRUFileID'):                    
            fruFileID = ipmiJson["BoardInfo"]["FRUFileID"]

        boardAreaObj = IpmiBoardRecord(formatVersion,languageCode,mfgTime,boardMfg, \
                                       boardName, boardSerial, boardPartNum,fruFileID )

    return boardAreaObj

# Parse IPMI chassis info area.
# This function extracts chassis information from the provided IPMI JSON object.
# See IPMI FRU specification for details.
def parse_chassis_info_area(ipmiJson, verbose = False):
    """
    Parses the chassis information area from a given IPMI JSON object.
    Args:
        ipmiJson (dict): The JSON object containing IPMI data.
        verbose (bool, optional): If True, prints chassis information details. Defaults to False.
    Returns:
        IpmiChassisRecord or None: An instance of IpmiChassisRecord containing parsed chassis information,
        or None if 'ChassisInfo' is not present in the input JSON.
    """
    
    formatVersion = 0
    chassisType = 0
    chassisPartNum = ""
    chassisSerialNum = ""
    chassisAreaObj = None

    if ipmiJson.get('ChassisInfo'):
        
        if verbose:         
            print("Chassis Info:")

        chassisInfo  = ipmiJson["ChassisInfo"]

        if chassisInfo.get('FormatVersion'):  
            formatVersion = ipmiJson["ChassisInfo"]["FormatVersion"]

        if chassisInfo.get('FormatVersion'):  
            chassisTypeString = ipmiJson["ChassisInfo"]["ChassisType"]
            if chassisTypeString == "Server":
                chassisType = 17

        if chassisInfo.get('ChassisPartNumber'):  
            chassisPartNum = ipmiJson["ChassisInfo"]["ChassisPartNumber"]

        if chassisInfo.get('ChassisSerialNumber'):          
            chassisSerialNum = ipmiJson["ChassisInfo"]["ChassisSerialNumber"]


        chassisAreaObj = IpmiChassisRecord(formatVersion,chassisType,chassisPartNum,chassisSerialNum)

    return chassisAreaObj


# Parse IPMI product info area.
# This function extracts product information from the provided IPMI JSON object.
# See IPMI FRU specification for details.
def parse_product_info_area(ipmiJson, verbose = False):

    productAreaObj = None
    formatVersion = 1
    languageCode = ""
    mfgName = ""
    productName = ""
    productModelNumber = ""
    productVersion = ""
    productSerialNumber =  ""
    assetTag = ""
    fruFileID = ""

    if ipmiJson.get('ProductInfo'):
        
        if verbose:             
            print("Product Info:")

        productInfo  = ipmiJson["ProductInfo"]

        if productInfo.get('FormatVersion'):  
            formatVersion = ipmiJson["ProductInfo"]["FormatVersion"]

        if productInfo.get('LanguageCode'):              
            languageCode = ipmiJson["ProductInfo"]["LanguageCode"]

        if productInfo.get('ManufacturerName'):              
            mfgName = ipmiJson["ProductInfo"]["ManufacturerName"]

        if productInfo.get('ProductName'):              
            productName = ipmiJson["ProductInfo"]["ProductName"]

        if productInfo.get('ProductModelNumber'):              
            productModelNumber = ipmiJson["ProductInfo"]["ProductModelNumber"]     

        if productInfo.get('ProductVersion'):  
            productVersion = ipmiJson["ProductInfo"]["ProductVersion"]

        if productInfo.get('ProductSerialNumber'):              
            productSerialNumber = ipmiJson["ProductInfo"]["ProductSerialNumber"]

        if productInfo.get('AssetTag'):  
            assetTag = ipmiJson["ProductInfo"]["AssetTag"]

        if productInfo.get('FRUFileID'):              
            fruFileID = ipmiJson["ProductInfo"]["FRUFileID"]

        productAreaObj = IpmiProductRecord(formatVersion,languageCode,mfgName,productName, \
                                       productModelNumber, productVersion, productSerialNumber, assetTag,fruFileID )

    return productAreaObj


# Parse HPM multirecord from input file
# This function extracts HPM multirecord information from the provided IPMI JSON object.
# See IPMI FRU specification and SCM 2.x specification for details.
def parse_hpm_multirecord(ipmiJson, verbose = False):
    """
    Parses the IPMI JSON object to extract the HPM (Hardware Platform Management) multirecord information.
    Args:
        ipmiJson (dict): The IPMI JSON object containing multirecords.
        verbose (bool, optional): If True, prints detailed information during parsing. Defaults to False.
    Returns:
        tuple:
            rc (bool): Indicates if the HPM multirecord was found (always False in current implementation).
            hpmMultirecordObj (HpmMultiRecord or None): An instance of HpmMultiRecord containing extracted fields if found, otherwise None.
    Notes:
        - Searches for a multirecord with "RecordType" equal to "HPM".
        - Extracts various fields such as FormatVersion, SCIRevisionMajor, SCIRevisionMinor, SCIVersionMajor,
            SCIVersionMinor, LTPIMajorVersion, LTPIMinorVersion, SCMType, HPMVendorID, and HPMDeviceID.
        - Prints progress and results if verbose is enabled.
    """
    rc = False
    hpmMultirecordObj = None
    ltpiVersionMinor = 0
    hpmDevID = 0
    formatVersion = 2

    if verbose:
        print("Looking for HPM MR")

    for multirecord in ipmiJson["Multirecords"]:

        recordType = multirecord["RecordType"]

        if recordType == "HPM":

            if verbose:             
                print("Found HPM MR")

            if multirecord.get('FormatVersion'):
                formatVersion = multirecord["FormatVersion"]

            if multirecord.get('SCIRevisionMajor'):
                sciRevisionMajor = multirecord["SCIRevisionMajor"]

            if multirecord.get('SCIRevisionMinor'):
                sciRevisionMinor = multirecord["SCIRevisionMinor"]

            if multirecord.get('SCIVersionMajor'):                
                sciVersionMajor =  multirecord["SCIVersionMajor"]

            if multirecord.get('SCIVersionMinor'):
                sciVersionMinor = multirecord["SCIVersionMinor"]

            if multirecord.get('LTPIMajorVersion'):                
                ltpiVersionMajor =multirecord["LTPIMajorVersion"]

            if multirecord.get('LTPIMinorVersion'):               
                ltpiVersionMinor =multirecord["LTPIMinorVersion"]

            if multirecord.get('SCMType'):                
                scmType =multirecord["SCMType"]

            if multirecord.get('HPMVendorID'):                
                hpmVendorID =multirecord["HPMVendorID"]

            if multirecord.get('HPMDeviceID'):                            
                hpmDevID =multirecord["HPMDeviceID"]

            hpmMultirecordObj = HpmMultiRecord(formatVersion, sciRevisionMajor, sciRevisionMinor, sciVersionMajor, sciVersionMinor,  \
                        ltpiVersionMajor, ltpiVersionMinor, scmType, hpmVendorID, hpmDevID)

            print(hpmMultirecordObj)

    if verbose:
        print("Done Looking for HPM MR")

    return rc, hpmMultirecordObj


# Parse Peripheral multirecord from input file
# This function extracts Peripheral multirecord information from the provided IPMI JSON object.
# See IPMI FRU specification and SCM 2.x specification for details.
def parse_peripheral_multirecord(ipmiJson, verbose = False):
    """
    Parses the given IPMI JSON object to find and extract the PERIPHERAL multirecord.
    Args:
        ipmiJson (dict): The IPMI JSON data containing multirecords.
        verbose (bool, optional): If True, prints detailed information during parsing. Defaults to False.
    Returns:
        tuple:
            rc (bool): Indicates if the PERIPHERAL multirecord was found (always False in current implementation).
            peripheralMultirecordObj (PeripheralMultiRecord or None): The extracted PeripheralMultiRecord object if found, otherwise None.
    Note:
        - The function searches for a multirecord with "RecordType" equal to "PERIPHERAL".
        - If found, it extracts 'FormatVersion', 'DeviceClass', and 'DeviceSubClass' fields, using default values if not present.
        - The function prints the found object if verbose is enabled.
    """
    rc = False
    peripheralMultirecordObj = None

    deviceClass = 0
    deviceSubClass = 0
    formatVersion = 1

    if verbose:                    
        print("Looking for PERIPHERAL MR")

    for multirecord in ipmiJson["Multirecords"]:

        recordType = multirecord["RecordType"]

        if recordType == "PERIPHERAL":

            if verbose:             
                print("Found PERIPHERAL MR")

            if multirecord.get('FormatVersion'):
                formatVersion = multirecord["FormatVersion"]

            if multirecord.get('DeviceClass'):
                deviceClass = multirecord["DeviceClass"]

            if multirecord.get('DeviceSubClass'):
                deviceSubClass = multirecord["DeviceSubClass"]

            peripheralMultirecordObj = PeripheralMultiRecord(formatVersion, deviceClass, deviceSubClass)

            print(peripheralMultirecordObj)

    return rc, peripheralMultirecordObj



# Parse the IPMI input JSON file.
def parse_ipmi_json_file(ipmi_json_file, verbose=False):
    """
    Parses an IPMI FRU JSON file and constructs an ImpiFruRecordSet object containing board, chassis, product, HPM multirecord, and peripheral multirecord information.
    Args:
        ipmi_json_file (str): Path to the IPMI FRU JSON file to be parsed.
        verbose (bool, optional): If True, prints the parsed JSON dictionary. Defaults to False.
    Returns:
        tuple:
            rc (bool): Return code indicating if an error occurred during parsing (True for error, False for success).
            ipmiObj (ImpiFruRecordSet or None): Object containing parsed FRU data if successful, None if an error occurred.
    """
    rc= False
 
    # Parse JSON from a file
    with open(ipmi_json_file, "r") as file:
        python_dict_from_file = json.load(file)

    if verbose:  
        print(python_dict_from_file)

    # Read the board area info to build the record
    boardAreaObj = parse_board_info_area(python_dict_from_file)

    # Read the chassis area info to build the record
    chassisAreaObj = parse_chassis_info_area(python_dict_from_file)

    # Read the product area info to build the record
    productAreaObj = parse_product_info_area(python_dict_from_file)

    # Read the HPM multirecord if present
    rc, hpmMultirecordObj = parse_hpm_multirecord(python_dict_from_file)
    if rc:
        printf("JSON HPM MR Format Error!")
        return rc, None

    rc, peripheralMultiRecord = parse_peripheral_multirecord(python_dict_from_file)
    if rc:
        printf("JSON PERIPHERAL MR Format Error!")
        return rc, None

    # Create a single object to store this data
    ipmiObj = ImpiFruRecordSet(boardAreaObj, chassisAreaObj, productAreaObj, hpmMultirecordObj, peripheralMultiRecord)

    return rc, ipmiObj





