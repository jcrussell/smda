import logging
import io

import lief

LOGGER = logging.getLogger(__name__)


class ElfFileLoader(object):

    @staticmethod
    def isCompatible(data):
        # check for ELF magic
        return data[:4] == b"\x7FELF"

    @staticmethod
    def getBaseAddress(binary):
        elffile = lief.parse(bytearray(binary))
        # Determine base address of binary
        #
        base_addr = 0
        candidates = [0xFFFFFFFFFFFFFFFF]
        for section in elffile.sections:
            if section.virtual_address:
                candidates.append(section.virtual_address - section.offset)
        if len(candidates) > 1:
            base_addr = min(candidates)
        return base_addr

    @staticmethod
    def mapData(binary):
        # ELFFile needs a file-like object...
        # Attention: for Python 2.x use the cStringIO package for StringIO
        elffile = lief.parse(bytearray(binary))
        base_addr = ElfFileLoader.getBaseAddress(binary)
        LOGGER.info("Assuming base address 0x%x for inference of reference counts (based on ELF header)", base_addr)

        # find begin of the first and end of the last section
        max_virt_section_offset = 0
        min_raw_section_offset = 0xFFFFFFFFFFFFFFFF
        for section in elffile.sections:
            # print("{:20s} 0x{:08x} - 0x{:08x} / 0x{:08x}".format(section.name, section.header.sh_addr, section.header.sh_offset, section.header.sh_size))
            if section.virtual_address:
                max_virt_section_offset = max(max_virt_section_offset, section.size + section.virtual_address)
                min_raw_section_offset = min(min_raw_section_offset, section.virtual_address)

        # copy binary to mapped_binary
        if max_virt_section_offset:
            mapped_binary = bytearray([0] * (max_virt_section_offset - base_addr))
            mapped_binary[0:min_raw_section_offset] = binary[0:min_raw_section_offset]
        for section in elffile.sections:
            if section.virtual_address:
                rva = section.virtual_address - base_addr
                mapped_binary[rva:rva + section.size] = section.content

        return bytes(mapped_binary)

    @staticmethod
    def getBitness(binary):
        # TODO add machine types whenever we add more architectures
        elffile = lief.parse(bytearray(binary))
        machine_type = elffile.header.machine_type
        return 64 if lief.ELF.ARCH.x86_64 else 32
