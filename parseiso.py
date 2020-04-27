#!/usr/bin/python3
"""
Extract a file (usually /boot/grub/grub.cfg) from an ISO image or list
directory contents.

Examples:

    python3 parseiso.py filename.iso --ls /
    python3 parseiso.py filename.iso --ls /boot/grub
    python3 parseiso.py filename.iso --path /boot/grub/grub.cfg
    python3 parseiso.py filename.iso --path /md5sum.txt
    python3 parseiso.py --help

"""

import argparse
import enum
import pathlib
import struct
import sys
import typing
from contextlib import contextmanager


class FormatError(Exception):
    pass


@contextmanager
def parse_iso(isofile):
    with open(isofile, 'rb') as f:
        # ISO9660: the first 32 KB are unused and can be used for other
        # purposes (e.g. hybrid CDs)
        f.seek(32768)
        descriptors = {}
        for d in parse_volume_descriptors(f):
            descriptors[d.dtype] = d
        try:
            primary = descriptors[VolumeDescriptor.Type.PRIMARY]
        except KeyError:
            raise FormatError('primary volume descriptor not found')
        walker = TreeWalker(f, primary)
        yield walker


class VolumeDescriptor(typing.NamedTuple):

    class Type(enum.Enum):
        BOOT_RECORD = 0
        PRIMARY = 1
        SUPPLEMENTARY = 2
        PARTITION = 3
        TERMINATOR = 255

    dtype: int           # 1
    identifier: bytes    # 5
    version: int         # 1
    data: bytes          # 2041

    def __repr__(self):
        return f'VolumeDescriptor(dtype={self.dtype})'


def parse_volume_descriptors(f):
    while True:
        d = parse_volume_descriptor(f)
        if d.dtype == VolumeDescriptor.Type.TERMINATOR:
            break
        yield d


def parse_volume_descriptor(f):
    block = f.read(2048)
    if len(block) != 2048:
        raise FormatError(
            f'truncated volume descriptor: {len(block)} bytes')
    d = VolumeDescriptor(
        dtype=VolumeDescriptor.Type(block[0]),
        identifier=block[1:6],
        version=block[6],
        data=block[7:],
    )
    if d.identifier != b'CD001':
        raise FormatError('bad volume descriptor identifier: {d.identifier!r}')
    if d.version != 1:
        raise FormatError('bad volume descriptor version: {d.version!r}')
    if d.dtype == VolumeDescriptor.Type.PRIMARY:
        return parse_primary_volume_descriptor(d)
    return d


class PrimaryVolumeDescriptor(typing.NamedTuple):

    dtype: int                                              # 1
    identifier: bytes                                       # 5
    version: int                                            # 1

    FORMAT = (
        '<B32s32s8sII32sHHHHHHIIIIII34s128s128s128s128s37s37s37s17s17s17s'
        '17sBB512s653s'
    )

    reserved1: int                                          # 1
    system_identifier: bytes                                # 32
    volume_identifier: bytes                                # 32
    reserved2: bytes                                        # 8
    number_of_sectors: int                                  # 4
    number_of_sectors_byteswapped: int                      # 4
    reserved3: bytes                                        # 32
    volume_set_size: int                                    # 2
    volume_set_size_byteswapped: int                        # 2
    volume_sequence_number: int                             # 2
    volume_sequence_number_byteswapped: int                 # 2
    sector_size: int                                        # 2
    sector_size_byteswapped: int                            # 2
    path_table_length: int                                  # 4
    path_table_length_byteswapped: int                      # 4
    first_sector_in_first_le_path_table: int                # 4
    first_sector_in_second_le_path_table: int               # 4
    first_sector_in_first_be_path_table_byteswapped: int    # 4
    first_sector_in_second_be_path_table_byteswapped: int   # 4
    root_directory_record: bytes                            # 34
    volume_set_idenifier: bytes                             # 128
    publisher_identifier: bytes                             # 128
    data_preparer_identifier: bytes                         # 128
    application_identifier: bytes                           # 128
    copyright_file_identifier: bytes                        # 37
    abstract_file_identifier: bytes                         # 37
    bibliographical_file_identifier: bytes                  # 37
    date_and_time_of_volume_creation: bytes                 # 17
    date_and_time_of_most_recent_modification: bytes        # 17
    date_and_time_when_volume_expires: bytes                # 17
    date_and_time_when_volume_is_effective: bytes           # 17
    check1: bytes                                           # 1
    check0: bytes                                           # 1
    reserved4: bytes                                        # 512
    reserved5: bytes                                        # 653

    assert struct.calcsize(FORMAT) == 2041

    def __repr__(self):
        return (
            f'VolumeDescriptor(dtype={self.dtype},'
            f' volume_identifier={self.volume_identifier.rstrip()!r},'
            f' data_preparer_identifier='
            f'{self.data_preparer_identifier.rstrip()!r},'
            f' date_and_time_of_volume_creation='
            f'{self.date_and_time_of_volume_creation!r}'
            f')'
        )

    def get_root_directory_record(self):
        return DirectoryRecord.from_bytes(self.root_directory_record)


def parse_primary_volume_descriptor(d):
    assert d.dtype == VolumeDescriptor.Type.PRIMARY
    d = PrimaryVolumeDescriptor(
        d.dtype, d.identifier, d.version,
        *struct.unpack(PrimaryVolumeDescriptor.FORMAT, d.data))
    if d.reserved1 != 0:
        raise FormatError('bad check1 field: {d.check1}')
    if d.volume_set_size != 1:
        raise FormatError('bad volume set size: {d.volume_set_size}')
    if d.volume_sequence_number != 1:
        raise FormatError('bad volume set size: {d.volume_sequence_number}')
    if d.sector_size != 2048:
        raise FormatError('bad sector size: {d.sector_size}')
    if d.check1 != 1:
        raise FormatError('bad check1 field: {d.check1}')
    if d.check0 != 0:
        raise FormatError('bad check0 field: {d.check1}')
    check_u32(d, 'number_of_sectors')
    check_u16(d, 'volume_set_size')
    check_u16(d, 'volume_sequence_number')
    check_u16(d, 'sector_size')
    check_u32(d, 'path_table_length')

    return d


def check_u32(obj, fieldname):
    check_byteswapped(obj, fieldname, 'I')


def check_u16(obj, fieldname):
    check_byteswapped(obj, fieldname, 'H')


def check_byteswapped(obj, fieldname, format):
    value = getattr(obj, fieldname)
    byteswapped = getattr(obj, f'{fieldname}_byteswapped')
    (byteswapped,) = struct.unpack(f'>{format}', struct.pack(f'<{format}', byteswapped))
    if value != byteswapped:
        raise FormatError(f'{fieldname} mismatch: {value} != {byteswapped}')


class DirectoryRecord(typing.NamedTuple):

    class Flags(enum.IntFlag):
        HIDDEN = 1 << 0
        DIRECTORY = 1 << 1
        ASSOCIATED_FILE = 1 << 2
        RECORD_FORMAT_SPECIFIED = 1 << 3
        PERMISSIONS_SPECIFIED = 1 << 4
        NOT_FINAL = 1 << 7

    FORMAT = '<BBIIIIBBBBBBBBBBHHB'

    record_size: int                           # 1
    extended_attribute_record_size: int        # 1
    first_sector: int                          # 4
    first_sector_byteswapped: int              # 4
    file_size: int                             # 4
    file_size_byteswapped: int                 # 4
    years_since_1900: int                      # 1
    month: int                                 # 1
    day: int                                   # 1
    hour: int                                  # 1
    minute: int                                # 1
    second: int                                # 1
    utc_offset: int                            # 1
    flags: int                                 # 1
    interleaved_file_unit_size: int            # 1
    interleave_gap_size: int                   # 1
    volume_sequence_number: int                # 2
    volume_sequence_number_byteswapped: int    # 2
    identifier_length: int                     # 1
    identifier: bytes                          # N
    padding: bytes                             # 0 or 1
    extra: bytes                               # M

    @property
    def name(self):
        if self.identifier == b'\x00':
            return '.'
        if self.identifier == b'\x01':
            return '..'
        return self.identifier.decode('ascii', 'replace')

    @property
    def is_directory(self):
        return self.flags & self.Flags.DIRECTORY != 0

    @property
    def has_extents(self):
        return self.flags & self.Flags.NOT_FINAL != 0

    @classmethod
    def from_bytes(cls, block):
        fields = struct.unpack_from(cls.FORMAT, block)
        d = cls(*fields, None, None, None)
        if d.record_size != len(block):
            raise FormatError(
                f'directory record size mismatch:'
                f' {d.record_size} != {len(block)}')
        if d.extended_attribute_record_size != 0:
            raise FormatError('bad extended attribute record size: {d.check1}')
        check_u32(d, 'first_sector')
        check_u32(d, 'file_size')
        check_u16(d, 'volume_sequence_number')
        offset = struct.calcsize(cls.FORMAT)
        padding_length = 1 - d.identifier_length % 2
        extra_length = (d.record_size - offset - d.identifier_length - padding_length)
        fmt = f'<{d.identifier_length}s{padding_length}s{extra_length}s'
        return cls(*fields, *struct.unpack_from(fmt, block, offset))

    def read_from(self, f):
        if self.file_size == 0:
            return b''
        f.seek(self.first_sector * 2048)
        data = f.read(self.file_size)
        if len(data) != self.file_size:
            raise FormatError('file truncated')
        return data

    def __repr__(self):
        return f'DirectoryRecord({self.identifier.rstrip()!r})'


def parse_directory(data):
    offset = 0
    while True:
        size = data[offset]
        if size == 0:
            break
        yield DirectoryRecord.from_bytes(data[offset:offset+size])
        offset += size


class TreeWalker:

    def __init__(self, f, primary_volume_descriptor):
        self.f = f
        self.primary_volume_descriptor = primary_volume_descriptor
        self.cache = {
            pathlib.PurePosixPath('/'): primary_volume_descriptor.get_root_directory_record()
        }

    def lookup(self, path) -> pathlib.PurePosixPath:
        path = pathlib.PurePosixPath(path)
        if not path.is_absolute():
            path = pathlib.PurePosixPath('/' + str(path))
        if path not in self.cache:
            parent = self.lookup(path.parent)
            for entry in self.listdir(parent):
                self.cache.setdefault(parent / entry.name, entry)
        alt_paths = [path, str(path).upper()]
        if ';' not in path.name:
            alt_path = str(path) + ';1'
            alt_paths += [alt_path, alt_path.upper()]
        for path in map(pathlib.PurePosixPath, alt_paths):
            if path in self.cache:
                return path
        raise FileNotFoundError(f'no such file or directory: {path}')

    def get(self, path) -> DirectoryRecord:
        path = self.lookup(path)
        return self.cache[path]

    def listdir(self, path) -> typing.Iterator[DirectoryRecord]:
        d = self.get(path)
        if not d.is_directory:
            raise NotADirectoryError(f'not a directory: {path}')
        return parse_directory(d.read_from(self.f))

    def read(self, path) -> bytes:
        d = self.get(path)
        if d.is_directory:
            raise IsADirectoryError(f'not a regular file: {path}')
        if d.has_extents:
            raise IsADirectoryError(f'{path} has multiple extents which is not supported')
        return d.read_from(self.f)


def main():
    parser = argparse.ArgumentParser(
        description="extact grub.cfg from an ISO image")
    parser.add_argument(
        "isofile", nargs='+', help="the ISO image file you want to inspect")
    parser.add_argument(
        "--path", default='/boot/grub/grub.cfg',
        help="filename of the file you want to extract (default: %(default)s)")
    parser.add_argument(
        "--ls", metavar='PATH', help="list the contents of this directory")
    args = parser.parse_args()
    for n, filename in enumerate(args.isofile):
        if len(args.isofile) > 1:
            if n > 0:
                print()
            print(f'#\n# {filename}\n#')
        try:
            with parse_iso(filename) as walker:
                if args.ls:
                    for entry in walker.listdir(args.ls):
                        print(entry.name + ('/' if entry.is_directory else ''))
                else:
                    sys.stdout.buffer.write(walker.read(args.path))
        except (OSError, FormatError) as e:
            print(e, file=sys.stderr)


if __name__ == "__main__":
    main()
