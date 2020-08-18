#!/usr/bin/python3
"""
Generate a grub.cfg that can boot Ubuntu ISO images.

Works with any Ubuntu ISO image that uses casper
(http://manpages.ubuntu.com/manpages/focal/man7/casper.7.html), which is every
desktop and live-server image.

Usage: mkgrubcfg.py -d path/to/directory/with/iso/images -o grub.cfg
"""

import argparse
import os
import re
import sys


HEADER = """
#
# Notes for adding new entries:
# - run python3 mkgrubcfg.py -o grub.cfg
#
# Testing in KVM (assuming this USB drive is mounted as /dev/sdb1):
# - run sh kvmboot /dev/sdb1
#   (if arrow keys don't work in the GRUB menu, use Ctrl-N/P)
#

""".lstrip()

ARCHS = {
    'i386': 'x86',
    'amd64': 'x86-64',
}

VARIANTS = {
    'desktop': 'desktop livecd',
    'live-server': 'server livecd',
}

KNOWN_COMMAND_LINES = {
    # if you wish to override a command line, or if the autodetection doesn't work,
    # you can do it like this:
    'ubuntu-16.04.6-server-amd64.iso': 'file=/cdrom/preseed/ubuntu-server.seed quiet ---',
    # NB: this is pointless for ubuntu 16.04 LTS images, they're known not to work:
    # they don't use casper, and debian-instaler doesn't know about iso-scan/filename=
    # and so the installation fails a couple of steps in when it fails to find the .deb files
}

KVM_OK = "Tested in KVM, works"
KVM_DESKTOP_OK = "Tested in KVM, works (boots into live session)"
KVM_SERVER_OK = "Tested in KVM, works (boots, haven't tried to complete installation)"
TEST_STATUS = {
    # images I have tested personally
    'ubuntu-20.04-desktop-amd64.iso': KVM_OK,
    'ubuntu-20.04-live-server-amd64.iso': KVM_OK,
    'ubuntu-20.04.1-desktop-amd64.iso': KVM_DESKTOP_OK,
    'ubuntu-20.04.1-live-server-amd64.iso': KVM_SERVER_OK,
    'ubuntu-19.10-desktop-amd64.iso': KVM_DESKTOP_OK,
    'ubuntu-18.04.3-desktop-amd64.iso': KVM_DESKTOP_OK,
    'ubuntu-18.04.4-desktop-amd64.iso': KVM_DESKTOP_OK,
    'ubuntu-18.04.3-live-server-amd64.iso': KVM_OK,
    'ubuntu-18.04.4-live-server-amd64.iso': KVM_OK,
    'ubuntu-18.04.5-live-server-amd64.iso': KVM_SERVER_OK,
    'ubuntu-16.04.6-desktop-i386.iso': KVM_DESKTOP_OK,
    # and this is why overriding the command line can be futile, when autodetection doesn't work:
    'ubuntu-16.04.6-server-amd64.iso': 'Does not work',
}

ENTRY = """
menuentry "{title}" {{
    # {test_status}
    set isofile="/ubuntu/{isofile}"
    loopback loop $isofile
    linux (loop){kernel} iso-scan/filename=$isofile {cmdline}
    initrd (loop){initrd}
}}

""".lstrip()

SUBMENU = """
submenu "{title} >" {{

{entries}

}} # end of submenu

""".lstrip()

FOOTER = """
menuentry "Memory test (memtest86+)" {
    linux16 /boot/mt86plus
}
""".lstrip()


class Error(Exception):
    pass


def find_iso_files(where):
    # We want to sort by Ubuntu version, in descending order, and then by image
    # type, in ascending alphabetical order.
    return sorted(
        sorted(fn for fn in os.listdir(where) if fn.endswith('.iso')),
        key=lambda fn: fn.split('-')[:2],
        reverse=True)


def group_files(files):
    groups = []
    current = []
    current_prefix = None
    for file in files:
        prefix = file[:len('ubuntu-XX.YY')]
        if prefix == current_prefix:
            current.append(file)
        else:
            if len(current) == 1:
                groups.extend(current)
            elif current:
                groups.append(current)
            current_prefix = prefix
            current = [file]
    if len(current) == 1:
        groups.extend(current)
    elif current:
        groups.append(current)
    return groups


def make_grub_cfg(entries, isodir):
    parts = [HEADER]
    for entry_or_group in entries:
        if isinstance(entry_or_group, list):
            title = mkgrouptitle(entry_or_group)
            parts.append(mksubmenu(title, [
                mkentry(entry, isodir) for entry in entry_or_group
            ]))
        else:
            parts.append(mkentry(entry_or_group, isodir))
    parts.append(FOOTER)
    return ''.join(parts)


def mkgrouptitle(isofiles):
    # ubuntu-XX.XX-variant-arch.iso
    ubuntu, release, rest = isofiles[0].rpartition('.')[0].split('-', 2)
    if is_lts(release):
        release += ' LTS'
    return f'Ubuntu {release}'


def mksubmenu(title, entries):
    return SUBMENU.format(
        title=title,
        entries=''.join(entries).rstrip(),
    )


def mkentry(isofile, isodir):
    try:
        return ENTRY.format(
            isofile=isofile,
            title=mktitle(isofile),
            test_status=mkteststatus(isofile),
            cmdline=mkcmdline(isofile, isodir),
            kernel='/casper/vmlinuz',
            initrd='/casper/initrd',  # some older releases had initrd.gz
        ).replace('\n    # \n', '\n')  # remove empty comments
    except Error as err:
        print(f"skipping {isofile}: {err}", file=sys.stderr)
        return ''


def mktitle(isofile):
    # ubuntu-XX.XX-variant-arch.iso
    try:
        ubuntu, release, rest = isofile.rpartition('.')[0].split('-', 2)
        if ubuntu != 'ubuntu':
            raise ValueError
        variant, arch = rest.rsplit('-', 1)
        if is_lts(release):
            release += ' LTS'
    except ValueError:
        raise Error(f'filename does not look like ubuntu-XX.XX-variant-arch.iso')
    return f'Ubuntu {release} ({ARCHS.get(arch, arch)} {VARIANTS.get(variant, variant)})'


def mkteststatus(isofile):
    return '\n    # '.join(get_test_status(isofile))


def get_test_status(isofile):
    test_status = TEST_STATUS.get(isofile, 'Untested')
    if not isinstance(test_status, list):
        test_status = [test_status]
    return test_status


def mkcmdline(isofile, isodir):
    # too risky to guess
    if isofile in KNOWN_COMMAND_LINES:
        cmdline = KNOWN_COMMAND_LINES[isofile]
    else:
        cmdline = extract_command_line_from_iso(os.path.join(isodir, isofile))

    if isinstance(cmdline, dict):
        cmdline = cmdline[None]
    return cmdline


def extract_command_line_from_iso(isofile):
    from parseiso import parse_iso, FormatError
    try:
        with parse_iso(isofile) as walker:
            grub_cfg = walker.read('/boot/grub/grub.cfg').decode('UTF-8', 'replace')
    except (OSError, FormatError) as e:
        raise Error(str(e))
    return extract_command_line_from_grub_cfg(grub_cfg)


def extract_command_line_from_grub_cfg(grub_cfg_text):
    rejected = []
    for menuentry, linux, kernel, cmdline in extract_grub_menu(grub_cfg_text):
        if (linux, kernel) == ('linux', '/casper/vmlinuz'):
            return cmdline
        rejected.append((menuentry, f"{linux} {kernel} {cmdline}"))
    error = 'could not find a suitable kernel command line in grub.cfg inside the ISO image'
    if rejected:
        error += '\nrejected, because they use the wrong kernel (not /casper/vmlinuz):\n'
        for menuentry, line in rejected:
            error += f'  menuentry "{menuentry}"\n    {line}\n'
        error += 'if you want to use one of these, edit mkgrubcfg.py and modify KNOWN_COMMAND_LINES'
    raise Error(error)


def extract_grub_menu(grub_cfg_text):
    menuentry_rx = re.compile(r'^\s*menuentry\s+"([^"]+)"')
    linux_rx = re.compile(r'^\s*(linux|linux16)\s+(\S+)\s+(\S.*)')
    menuentry = None
    for line in grub_cfg_text.splitlines():
        m = menuentry_rx.match(line)
        if m:
            menuentry = m.group(1)
        m = linux_rx.match(line)
        if m:
            linux, kernel, cmdline = m.groups()
            yield (menuentry, linux, kernel, cmdline)


def is_lts(release):
    major, minor = map(int, release.split('.')[:2])
    # 6.06 was the first LTS release; since then there's been an LTS every two
    # years: 8.04, 10.04, 12.04, 14.04, 16.04, 18.04 and 20.04.
    # we can ignore the past and focus on the current pattern.
    return major % 2 == 0 and minor == 4


def print_groups(groups):
    for group in groups:
        if not isinstance(group, list):
            group = [group]
        print(f'# {mkgrouptitle(group)}')
        for isofile in group:
            width = 40
            test_status = f'{" ":<{width}}  # '.join(get_test_status(isofile))
            print(f'{isofile:<{width}}  # {test_status}')


def main():
    parser = argparse.ArgumentParser(description="create a grub.cfg for Ubuntu ISO images")
    parser.add_argument("--list", action='store_true', help='list found ISO images')
    parser.add_argument("-d", "--iso-dir", metavar='DIR', default="../../ubuntu",
                        help="directory with ISO images (default: %(default)s)")
    parser.add_argument("-o", metavar='FILENAME', dest='outfile', default="-",
                        help="write the generated grub.cfg to this file (default: stdout)")
    args = parser.parse_args()

    try:
        iso_files = find_iso_files(args.iso_dir)
        groups = group_files(iso_files)
        if args.list:
            print_groups(groups)
            return
        grub_cfg = make_grub_cfg(groups, args.iso_dir)
        if args.outfile != '-':
            with open(args.outfile, 'w') as f:
                f.write(grub_cfg)
        else:
            print(grub_cfg, end="")
    except Error as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
