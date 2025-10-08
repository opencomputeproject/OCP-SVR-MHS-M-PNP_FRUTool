# SPDX-FileCopyrightText: 2025 Hewlett Packard Enterprise Development LP
# SPDX-License-Identifier: MIT

# FUnpack.py
# Enhanced tool to extract components from a combined FRU image file with gzip detection
# Inputs:
#   Combined FRU image file (binary)
# Outputs:
#   Extracted components: IPMI FRU section, DMTF FRU section, and individual files
#   Automatic detection and decompression of gzipped files

import os
import sys
import struct
import ctypes
import gzip
import uuid
import zlib
from ctypes import *
from utility import *

# Constants (from dmtfpack.py)
IPMI_IMAGE_SIZE_MINIMUM = 256
DMTF_FRU_IDENTIFIER = 0x1AB4  # 2 bytes
DMTF_FRU_VERSION = 1  # 1 byte
DMTF_FRU_HEADER_FORMAT = "<HBBI"  # identifier (H), version (B), file_count (B), reserved (I)
FDT_ENTRY_FORMAT = "<16sIIIHHII"  # FDT entry format: UUID(16), version(4), size(4), offset(4), flags(2), reserved(2), context(4), checksum(4)
FDT_ENTRY_SIZE = 40  # Should always be 40 bytes per spec
DMTF_FRU_HEADER_SIZE = 8

# Default format identifiers
DMTF_GENERAL_FRU_RECORD_FILE = "a4f59e2c-b8a9-4fad-b092-41332c90e65b"

# Compression flag bit positions (from dmtfpack.py)
COMPRESSION_GZIP_FLAG = 0b0010
COMPRESSION_MESSAGEPACK_FLAG = 0b0001
COMPRESSION_ANOTHER_FLAG = 0b0011

#tool version
FUNPACK_TOOL_VERSION = 1

class FdtEntry:
    """File Descriptor Table Entry structure"""
    def __init__(self, formatId="", version=0, size=0, offset=0, flags=0, context=0, checksum=0):
        self.formatId = formatId
        self.version = version
        self.size = size
        self.offset = offset
        self.flags = flags
        self.context = context
        self.checksum = checksum
        
    def is_gzipped(self):
        """Check if this file is marked as gzipped"""
        return (self.flags & COMPRESSION_GZIP_FLAG) != 0
    
    def get_compression_type(self):
        """Get the compression type as a string"""
        if self.flags & COMPRESSION_GZIP_FLAG:
            return "gzip"
        elif self.flags & COMPRESSION_MESSAGEPACK_FLAG:
            return "messagepack"
        elif self.flags & COMPRESSION_ANOTHER_FLAG:
            return "another"
        else:
            return "none"

    def __str__(self):
        return f"FDT: {self.formatId[:8]}... v{self.version} size:{self.size} offset:{self.offset} flags:0x{self.flags:04x} compression:{self.get_compression_type()}"

def parse_fdt_entry(fdt_data):
    """Parse a single FDT entry from binary data"""
    uuid_bytes, version, size, offset, flags, reserved, context, checksum = struct.unpack(FDT_ENTRY_FORMAT, fdt_data)
    
    # Convert UUID bytes back to string
    uuid_obj = uuid.UUID(bytes=uuid_bytes)
    format_id = str(uuid_obj)
    
    return FdtEntry(format_id, version, size, offset, flags, context, checksum)

def extract_ipmi_section(image_buf, verbose=False):
    """Extract IPMI FRU section from the image"""
    if verbose:
        print("Extracting IPMI FRU section...")

    # IPMI section starts at the beginning of the image buffer
    ipmi_buf = image_buf[:IPMI_IMAGE_SIZE_MINIMUM]

    if verbose:
        hexdump("IPMI FRU Section:", ipmi_buf, 0, min(64, len(ipmi_buf)), verbose)

    return ipmi_buf

def extract_dmtf_section(image_buf, ipmi_size, verbose=False):
    """Extract DMTF FRU section from the image"""
    if verbose:
        print("Extracting DMTF FRU section...")

    dmtf_buf = image_buf[ipmi_size:]

    if verbose:
        hexdump("DMTF FRU Section:", dmtf_buf, 0, min(64, len(dmtf_buf)), verbose)

    return dmtf_buf

def parse_dmtf_header(dmtf_buf, verbose=False):
    """Parse DMTF FRU header and return file count"""
    if len(dmtf_buf) < DMTF_FRU_HEADER_SIZE:
        if verbose:
            print("Error: DMTF buffer too small for header")
        return None
    
    header_data = dmtf_buf[:DMTF_FRU_HEADER_SIZE]
    identifier, version, file_count, reserved = struct.unpack(DMTF_FRU_HEADER_FORMAT, header_data)

    if verbose:
        print(f"DMTF Identifier: 0x{identifier:04x}")
        print(f"DMTF Version: {version}")
        print(f"Number of files: {file_count}")
        print(f"Reserved: {reserved}")

    return {
        'identifier': identifier,
        'version': version,
        'file_count': file_count,
        'reserved': reserved
    }

def parse_file_descriptor_table(dmtf_buf, file_count, verbose=False):
    """Parse the File Descriptor Table and return list of FdtEntry objects"""
    if verbose:
        print("Parsing File Descriptor Table...")

    fdt_entries = []
    offset = DMTF_FRU_HEADER_SIZE
    
    for i in range(file_count):
        if offset + FDT_ENTRY_SIZE > len(dmtf_buf):
            print(f"Error: Not enough data for FDT entry {i}")
            break
            
        fdt_data = dmtf_buf[offset:offset + FDT_ENTRY_SIZE]
        fdt_entry = parse_fdt_entry(fdt_data)
        fdt_entries.append(fdt_entry)
        
        if verbose:
            print(f"FDT Entry {i}: {fdt_entry}")
            if fdt_entry.is_gzipped():
                print(f"  -> File {i} is GZIPPED!")
        
        offset += FDT_ENTRY_SIZE

    return fdt_entries

def extract_and_decompress_file(dmtf_buf, fdt_entry, file_index, output_dir, verbose=False):
    """Extract a single file from DMTF buffer, decompressing if necessary"""
    
    # Validate offset and size
    if fdt_entry.offset + fdt_entry.size > len(dmtf_buf):
        print(f"Error: File {file_index} extends beyond buffer bounds")
        return None
    
    # Extract file data
    file_data = dmtf_buf[fdt_entry.offset:fdt_entry.offset + fdt_entry.size]
    
    # Determine output filename
    if fdt_entry.is_gzipped():
        original_filename = f"file_{file_index}_compressed.gz"
        decompressed_filename = f"file_{file_index}_decompressed.bin"
    else:
        original_filename = f"file_{file_index}.bin"
        decompressed_filename = None
    
    # Write original file
    original_path = os.path.join(output_dir, original_filename)
    with open(original_path, "wb") as f:
        f.write(file_data)
    
    if verbose:
        print(f"Extracted {original_filename} ({len(file_data)} bytes)")
    
    # If file is gzipped, also write decompressed version
    if fdt_entry.is_gzipped():
        try:
            decompressed_data = gzip.decompress(file_data)
            decompressed_path = os.path.join(output_dir, decompressed_filename)
            
            with open(decompressed_path, "wb") as f:
                f.write(decompressed_data)
            
            compression_ratio = len(file_data) / len(decompressed_data) * 100
            
            if verbose:
                print(f"Decompressed to {decompressed_filename} ({len(decompressed_data)} bytes, {compression_ratio:.1f}% compression)")
            
            return {
                'original': original_path,
                'decompressed': decompressed_path,
                'compressed_size': len(file_data),
                'decompressed_size': len(decompressed_data),
                'compression_ratio': compression_ratio
            }
            
        except Exception as e:
            print(f"Error decompressing file {file_index}: {e}")
            return {
                'original': original_path,
                'error': str(e)
            }
    else:
        return {
            'original': original_path,
            'size': len(file_data)
        }

def extract_files_from_dmtf(dmtf_buf, output_dir, verbose=False):
    """Parse and extract files from DMTF FRU section with gzip detection"""
    
    # Parse DMTF header
    header_info = parse_dmtf_header(dmtf_buf, verbose)
    if not header_info:
        return []
    
    file_count = header_info['file_count']
    if file_count == 0:
        if verbose:
            print("No files found in DMTF section")
        return []
    
    # Parse File Descriptor Table
    fdt_entries = parse_file_descriptor_table(dmtf_buf, file_count, verbose)
    
    # Check for gzipped files
    gzipped_files = [i for i, fdt in enumerate(fdt_entries) if fdt.is_gzipped()]
    if gzipped_files:
        print(f"\n GZIP DETECTED: Found {len(gzipped_files)} gzipped file(s) at indices: {gzipped_files}")
        for i in gzipped_files:
            print(f"   File {i}: {fdt_entries[i].get_compression_type()} compression")
    else:
        print("\n No gzipped files detected in this image")
    
    # Extract all files
    extraction_results = []
    for i, fdt_entry in enumerate(fdt_entries):
        if verbose:
            print(f"\nExtracting file {i}...")
        
        result = extract_and_decompress_file(dmtf_buf, fdt_entry, i, output_dir, verbose)
        if result:
            result['index'] = i
            result['fdt_entry'] = fdt_entry
            extraction_results.append(result)
    
    return extraction_results

def generate_extraction_report(extraction_results, output_dir, verbose=False):
    """Generate a detailed extraction report"""
    report_path = os.path.join(output_dir, "extraction_report.txt")
    
    with open(report_path, "w") as f:
        f.write("FUnpack Extraction Report\n")
        f.write("=" * 50 + "\n\n")
        
        gzipped_count = sum(1 for result in extraction_results if result['fdt_entry'].is_gzipped())
        total_files = len(extraction_results)
        
        f.write(f"Total files extracted: {total_files}\n")
        f.write(f"Gzipped files found: {gzipped_count}\n")
        f.write(f"Regular files: {total_files - gzipped_count}\n\n")
        
        if gzipped_count > 0:
            f.write("GZIPPED FILES DETECTED:\n")
            f.write("-" * 30 + "\n")
            
            total_compressed_size = 0
            total_decompressed_size = 0
            
            for result in extraction_results:
                if result['fdt_entry'].is_gzipped():
                    f.write(f"\nFile {result['index']}:\n")
                    f.write(f"  Format ID: {result['fdt_entry'].formatId}\n")
                    f.write(f"  Compression: {result['fdt_entry'].get_compression_type()}\n")
                    f.write(f"  Original file: {os.path.basename(result['original'])}\n")
                    
                    if 'decompressed' in result:
                        f.write(f"  Decompressed file: {os.path.basename(result['decompressed'])}\n")
                        f.write(f"  Compressed size: {result['compressed_size']} bytes\n")
                        f.write(f"  Decompressed size: {result['decompressed_size']} bytes\n")
                        f.write(f"  Compression ratio: {result['compression_ratio']:.1f}%\n")
                        
                        total_compressed_size += result['compressed_size']
                        total_decompressed_size += result['decompressed_size']
                    elif 'error' in result:
                        f.write(f"  Decompression error: {result['error']}\n")
            
            if total_decompressed_size > 0:
                overall_ratio = total_compressed_size / total_decompressed_size * 100
                f.write(f"\nOverall compression statistics:\n")
                f.write(f"  Total compressed size: {total_compressed_size} bytes\n")
                f.write(f"  Total decompressed size: {total_decompressed_size} bytes\n")
                f.write(f"  Overall compression ratio: {overall_ratio:.1f}%\n")
        
        f.write(f"\nRegular files:\n")
        f.write("-" * 15 + "\n")
        for result in extraction_results:
            if not result['fdt_entry'].is_gzipped():
                f.write(f"File {result['index']}: {os.path.basename(result['original'])} ({result['size']} bytes)\n")
    
    if verbose:
        print(f"\nExtraction report written to: {report_path}")
    
    return report_path

def main():
    """
    Main entry point for the Enhanced FRU Image Extraction Tool with Gzip Detection.
    Parses command-line arguments to specify input and output files, verbosity, and extraction options.
    Extracts components from a combined FRU image file, automatically detecting and decompressing gzipped files.
    Command-line arguments:
        -i, --input      : Combined FRU image file (required).
        -o, --output     : Output directory for extracted components (required).
        -v, --verbose    : Enable verbose output (optional).
        --skip-ipmi      : Skip IPMI section extraction (optional).
        --skip-dmtf      : Skip DMTF section extraction (optional).
        --report         : Generate detailed extraction report (optional).
    Prints the tool version, extraction progress, and summary information.
    """
    import argparse

    toolversion = FUNPACK_TOOL_VERSION
    print("")
    print(f"Enhanced FRU Image Extraction Tool with Gzip Detection Version {toolversion}")

    parser = argparse.ArgumentParser(description="Extract components from a combined FRU image file with gzip detection")
    parser.add_argument("-i", "--input", required=True, help="Combined FRU image file")
    parser.add_argument("-o", "--output", required=True, help="Output directory for extracted components")
    parser.add_argument("-v", "--verbose", action="store_true", required=False, help="Verbose output")
    parser.add_argument("--skip-ipmi", action="store_true", required=False, help="Skip IPMI section extraction")
    parser.add_argument("--skip-dmtf", action="store_true", required=False, help="Skip DMTF section extraction")
    parser.add_argument("--report", action="store_true", required=False, help="Generate detailed extraction report")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: {args.input} is not a valid file.")
        sys.exit(1)

    if not os.path.exists(args.output):
        os.makedirs(args.output)
        if args.verbose:
            print(f"Created output directory: {args.output}")

    # Read the entire image
    with open(args.input, "rb") as f:
        image_buf = f.read()

    print(f"Loaded FRU image: {len(image_buf)} bytes")

    extraction_results = []

    # Extract IPMI section
    if not args.skip_ipmi:
        ipmi_buf = extract_ipmi_section(image_buf, args.verbose)
        ipmi_output = os.path.join(args.output, "ipmi_section.bin")
        with open(ipmi_output, "wb") as f:
            f.write(ipmi_buf)

        print(f" IPMI section extracted to {ipmi_output} ({len(ipmi_buf)} bytes)")

    # Extract DMTF section and files
    if not args.skip_dmtf:
        dmtf_buf = extract_dmtf_section(image_buf, IPMI_IMAGE_SIZE_MINIMUM, args.verbose)
        dmtf_output = os.path.join(args.output, "dmtf_section.bin")
        with open(dmtf_output, "wb") as f:
            f.write(dmtf_buf)

        print(f" DMTF section extracted to {dmtf_output} ({len(dmtf_buf)} bytes)")

        # Extract individual files from DMTF section
        extraction_results = extract_files_from_dmtf(dmtf_buf, args.output, args.verbose)

    # Generate report if requested
    if args.report and extraction_results:
        report_path = generate_extraction_report(extraction_results, args.output, args.verbose)
        print(f" Detailed report generated: {report_path}")

    # Summary
    gzipped_count = sum(1 for result in extraction_results if result['fdt_entry'].is_gzipped())
    total_files = len(extraction_results)
    
    print(f"\n Extraction Summary:")
    print(f"   Total files: {total_files}")
    print(f"   Gzipped files: {gzipped_count}")
    print(f"   Regular files: {total_files - gzipped_count}")
    
    if gzipped_count > 0:
        print(f"\n  Gzip compression was detected and files were automatically decompressed!")
    
    print(" Extraction completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
