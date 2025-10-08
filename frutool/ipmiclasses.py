# SPDX-FileCopyrightText: 2025 Hewlett Packard Enterprise Development LP
# SPDX-License-Identifier: MIT

# IPMI FRU records representation classes
# This module contains classes that represent various IPMI FRU records.
# See the IPMI,  DC-SCM, and M-PNP specifications for details on the structure of these records.

from ctypes import *    # crc16
from utility import *

#############################################################################
# Simple classes used to store IPMI record data

# This is per the DSP0220 spec
DEFAULT_DMTF_OEM_RECORD_MFG_ID = 0xB41A00

# FDT entry contents from DSP0220
class DmtfOemRecord:
    def __init__(self, dmtfFruOffset = 0, mfgId = DEFAULT_DMTF_OEM_RECORD_MFG_ID):
        self.mfgId = mfgId
        self.dmtfFruOffset = dmtfFruOffset

    def __str__(self):
        return f"{self.mfgId}({self.dmtfFruOffset}))"

# IPMI chassis contents from IPMI spec
class IpmiChassisRecord:
    def __init__(self, formatVersion = 1, chassisType = 0, chassisPartNumber = "", chassisSerialNumber = ""):
        self.formatVersion = formatVersion
        self.chassisType = chassisType
        self.chassisPartNumber = chassisPartNumber
        self.chassisSerialNumber = chassisSerialNumber

    def __str__(self):
        return f"{self.formatVersion}({self.chassisType})({self.chassisPartNumber})({self.chassisSerialNumber})"

# IPMI board contents from IPMI spec
class IpmiBoardRecord:
    def __init__(self, formatVersion = 1, languageCode = 0,  mfgTime = "", boardMfg = "", boardName="", boardSerial = "", boardPartNum = "", fruFileID = ""):
        self.formatVersion = formatVersion
        self.languageCode = languageCode
        self.mfgTime = mfgTime
        self.boardMfg = boardMfg
        self.boardName = boardName
        self.boardSerial = boardSerial
        self.boardPartNum = boardPartNum
        self.fruFileID = fruFileID

    def __str__(self):
        return f"{self.formatVersion}({self.languageCode})({self.mfgTime})({self.boardMfg}) \
            ({self.boardName})({self.boardSerial})({self.boardPartNum})({self.fruFileID})"

# IPMI product info contents from IPMI spec
class IpmiProductRecord:
    def __init__(self, formatVersion = 1, languageCode = 0,  mfgName = "", productName = "", \
                 productNum ="", productVersion = "", productSerialNum = "", assetTag = "", fruFileID = ""):
        self.formatVersion = formatVersion
        self.languageCode = languageCode
        self.mfgName = mfgName
        self.productName = productName
        self.productNum = productNum
        self.productVersion = productVersion
        self.productSerialNum = productSerialNum
        self.assetTag = assetTag        
        self.fruFileID = fruFileID

    def __str__(self):
        return f"{self.formatVersion}({self.languageCode})({self.mfgName})({self.productName}) \
            ({self.productNum})({self.productVersion})({self.productSerialNum})({self.assetTag})({self.fruFileID})"

# IPMI superset class
class ImpiFruRecordSet:
    def __init__(self, board_rec = None, chassis_rec = None, product_rec = None, hpm_rec = None, periph_rec = None):
        
        self.boardRecord = board_rec
        self.chassisRecord = chassis_rec
        self.productRecord = product_rec
        self.hpmRecord = hpm_rec
        self.peripheralMultiRecord = periph_rec

    def __str__(self):
        return f"{self.boardRecord}({self.chassisRecord})({self.productRecord})"
 

# HPM multirecord contents from DC-SCM spec
class HpmMultiRecord:
    def __init__(self, formatVersion = 1, sciRevisionMajor = 2, sciRevisionMinor = 2, sciVersion = 33,  \
                  ltpiRevisionMajor = 1, ltpiRevisionMinor = 1,  ltpiVersion = 33,  scmType = 1,  hpmVendorID = 0, hpmDevID = 0):

        self.formatVersion = formatVersion
        self.sciRevisionMajor = sciRevisionMajor   
        self.sciRevisionMinor = sciRevisionMinor                

        self.sciVersion = sciVersion
    
        self.ltpiRevisionMajor = ltpiRevisionMajor
        self.ltpiRevisionMinor = ltpiRevisionMinor    

        self.ltpiVersion = ltpiVersion

        self.scmType = scmType

        self.hpmVendorID = hpmVendorID
        self.hpmDevID = hpmDevID


    def __str__(self):
        return f"{self.formatVersion}({self.sciRevisionMajor})({self.sciRevisionMinor})({self.sciVersion})({self.ltpiRevisionMajor})({self.ltpiRevisionMinor})({self.ltpiVersion})({self.scmType})({self.hpmVendorID})({self.hpmDevID})"


# Peripheral multirecord contents from MPNP FRU spec
class PeripheralMultiRecord:
    def __init__(self, formatVersion = 1, peripheralDeviceClass = 0, peripheralDeviceSubClass = 0):

        self.formatVersion = formatVersion
        self.peripheralDeviceClass = peripheralDeviceClass   
        self.peripheralDeviceSubClass = peripheralDeviceSubClass                


    def __str__(self):
        return f"{self.formatVersion}({self.peripheralDeviceClass})({self.peripheralDeviceSubClass})"
