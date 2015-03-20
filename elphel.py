'''
Created on Mar 20, 2015

@author: yuri
'''
import ctypes
import os
import mmap
import struct

class phys_mem:
    '''
    For the allocated physical memory not to be accidentially
    re-allocated by any other process, the process which
    allocated it should remain working
    '''
    def __init__(self, buf_size = 4096):
        ctypes_alloc = ctypes.CDLL('libelphel.so.0').malloc_and_mlock
        ctypes_alloc.restype = ctypes.c_void_p
        ctypes_alloc.argtypes = ctypes.c_size_t,
        self.endian="<" # little, ">" for big
        self.page_size = int(os.sysconf("SC_PAGE_SIZE")) & 0x7FFFFFFFFFFFFF
        self.pagemap_entry_size = 8
        self.size = buf_size
        if self.size > self.page_size:
            print("Only one page can be continuously\
                allocated from userspace\n")
            self.size = self.page_size
        self.virt_start_addr = ctypes_alloc(self.size)
        self.pid = os.getpid()
        self.__get_pagemap_entry()
        self.offset = self.virt_start_addr & (self.page_size-1)
        self.start_addr =  int(self.page*self.page_size+self.offset) & 0x7FFFFFFFFFFFFF
        self.end_addr = int(self.start_addr+self.size) & 0x7FFFFFFFFFFFFF

    def __get_pagemap_entry(self):
        maps_path = "/proc/{0}/pagemap".format(self.pid)
        if not os.path.isfile(maps_path):
            print("Process {0} doesn't exist.".format(self.pid))
            return
        offset  = (self.virt_start_addr / self.page_size) * \
            self.pagemap_entry_size
        with open(maps_path, 'r') as f:
            f.seek(offset, 0)
            self.page = \
                (struct.unpack('Q', f.read(self.pagemap_entry_size))[0])\
                & 0x7FFFFFFFFFFFFF
    
    def display(self):
        with open("/dev/mem", "r+b") as f:
            for addr in range (self.start_addr,self.end_addr+4,4):
                page_addr=addr & (~(self.page_size-1))
                if (addr == self.start_addr) or ((addr & 0x3f) == 0):
                    print ("\n0x%08x:"%addr),
                    page_offs=addr-page_addr
                mm = mmap.mmap(f.fileno(), self.page_size, offset=page_addr)
                data=struct.unpack(self.endian+"L",mm[page_offs:page_offs+4])
                d=data[0]
                print ("%08x"%d),
                mm.close()

    def fill(self, value=0x1e):
        with open("/dev/mem", "r+b") as f:
            count = 0
            for addr in range (self.start_addr,self.end_addr,1):
                page_addr=addr & (~(self.page_size-1))
                if page_addr != self.start_addr & (~(self.page_size-1)):
                    break
                page_offs=addr-page_addr
                mm = mmap.mmap(f.fileno(), self.page_size, offset=page_addr)
                mm[page_offs] = struct.pack("B",value)
                count += 1
                mm.close()
            print(str(count)+" bytes written.")

    def get_address(self):
        return self.start_addr
    
    def get_size(self):
        return self.size
