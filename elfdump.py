# elf file disassembler

import sys
from ctypes import *

''' ELF file main Header format:
Byte	ident[16]; 0x7f 3 chars; class; encoding; version; 
Short	type
Short	machine
Long 	version
Long	entry
Long	phoff
Long	shoff
Long	flags
Short	ehsize
Short	phentsize
Short	phnum
Short	shentsize
Short	shnum
Short	shstrndx
'''

# named constants
EI_MAG0, EI_MAG1, EI_MAG2, EI_MAG3, EI_CLASS, EI_DATA, EI_VERSION, EI_PAD, EI_NIDENT = range(8) + [16]
ELFMAG0, ELFMAG1, ELFMAG2, ELFMAG3 = 0x7F, 'E', 'L', 'F'
ELFCLASSNONE, ELFCLASS32, ELFCLASS64 = range(3)
ELFDATANONE, ELFDATA2LSB, ELFDATA2MSB = range(3)
ET_NONE, ET_REL, ET_EXEC, ET_DYN, ET_CORE = range(5)
EM_NONE, EM_M32, EM_SPARC, EM_386, EM_68K, EM_88K, EM_86O, EM_MIPS, EM_ARM = range(6) + [7,8,0x28]

def elfHeader(base):
	class elfHeaderBase(base):
		_fields_ = [('ident', c_ubyte * EI_NIDENT),
					('type', c_ushort),
					('machine', c_ushort),
					('version', c_uint32),
					('entry', c_uint32),
					('phoff', c_uint32),
					('shoff', c_uint32),
					('flags', c_uint32),
					('ehsize', c_ushort),
					('phentsize', c_ushort),
					('phnum', c_ushort),
					('shentsize', c_ushort),
					('shnum', c_ushort),
					('shstrndx', c_ushort)]
	return elfHeaderBase()

# format of program headers used to find image sections
def programHeader(base):
	class programHeaderBase(base):
		_fields_ = [('p_type', c_uint32),
					('p_offset', c_uint32),
					('p_vaddr', c_uint32),
					('p_paddr', c_uint32),
					('p_filesz', c_uint32),
					('p_memsz', c_uint32),
					('p_flags', c_uint32),
					('p_align', c_uint32)]
	return programHeaderBase()

# interpretations
classes = {ELFCLASSNONE:'invalid class', ELFCLASS32:'32-bit objects', ELFCLASS64:'64-bit objects'}
encodings = {ELFDATANONE:'invalid data encoding', ELFDATA2LSB:'little endian', ELFDATA2MSB:'big endian'}
types = {ET_NONE:'no file type', ET_REL:'relocatable file', ET_EXEC:'executable file', ET_DYN:'shared object file', ET_CORE:'corefile'}
machines = {EM_NONE:'no machine', EM_M32:'AT&T WE 32100', EM_SPARC:'SPARC', EM_386:'Intel 80386', EM_68K:'Motorola 68000', EM_88K:'Motorola 88000', EM_86O:'Intel 80860', EM_MIPS:'MIPS RS3000', EM_ARM:'ARM'}

def ehDump(elf):
	print 'ident: %s'%chr(elf.ident[EI_MAG1])+chr(elf.ident[EI_MAG2])+chr(elf.ident[EI_MAG3])
	print 'class: %s'%classes.get(elf.ident[EI_CLASS], str(elf.ident[EI_CLASS]))
	print 'encoding: %s'%encodings.get(elf.ident[EI_DATA], str(elf.ident[EI_DATA]))
	print 'version: %d'%elf.ident[EI_VERSION]
	print 'type: %s'%types.get(elf.type, str(elf.type))
	print 'machine: %s'%machines.get(elf.machine, str(elf.machine))
	print 'version: %d'%elf.version
	print 'entry: 0x%X'%elf.entry
	print 'phoff: %d'%elf.phoff
	print 'shoff: %d'%elf.shoff
	print 'flags: 0x%X'%elf.flags
	print 'ehsize: %d'%elf.ehsize
	print 'phentsize: %d'%elf.phentsize
	print 'phnum: %d'%elf.phnum
	print 'shentsize: %d'%elf.shentsize
	print 'shnum: %d'%elf.shnum
	print 'shstrndx: %d'%elf.shstrndx

def phDump(ph):
	print 'p_type:', ph.p_type
	print 'p_offset', ph.p_offset
	print 'p_vaddr 0x%X'%ph.p_vaddr
	print 'p_paddr 0x%X'%ph.p_paddr
	print 'p_filesz', ph.p_filesz
	print 'p_memsz', ph.p_memsz
	print 'p_flags 0x%X'%ph.p_flags
	print 'p_align', ph.p_align

def elfDump(file):
	# determine endian
	file = open(file, 'rb')
	file.seek(EI_DATA)
	if ord(file.read(1)) == ELFDATA2MSB:
		endian = BigEndianStructure
	else:
		endian = LittleEndianStructure

	# elf header
	elf = elfHeader(endian)
	file.seek(EI_MAG0)
	file.readinto(elf)
	
	
	ehDump(elf)
	
	# program header
	ph = programHeader(endian)
	size = 0
	image = []
	
	if elf.type == ET_EXEC:
		for i in range(elf.phnum):
			print 'PH#',i
			file.seek(elf.phoff + i * sizeof(ph))
			file.readinto(ph)
			phDump(ph)
			size += ph.p_filesz
			# image
			file.seek(ph.p_offset)
			image += file.read(ph.p_filesz)
		print 'size', size
		print 'image length:',len(image)

	file.close()

if __name__ == "__main__":
	elfDump(sys.argv[1])