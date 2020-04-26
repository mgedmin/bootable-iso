#!/usr/bin/python3

HEADER = """
#
# Notes for adding new entries:
# - launch mc, find the iso, press Enter
# - inside the ISO find /boot/grub/grub.cfg, look inside
#   be sure to add iso-scan/filename=$isofile before the -- or ---
#   (some ISOs have a loopback.cfg that already have this)
#
# Testing in KVM:
# - udisksctl unmount -b /dev/sdb1
# - sudo setfacl -m user:$USER:rw /dev/sdb
# - kvm -m 2048 -k en-us -drive format=raw,file=/dev/sdb
#   (if arrow keys don't work in the GRUB menu, use Ctrl-N/P)
# - udisksctl mount -b /dev/sdb1
#

""".lstrip()

ARCHS = {
    'amd64': 'x86-64',
}

VARIANTS = {
    'desktop': 'desktop livecd',
    'live-server': 'server livecd',
}

TEST_STATUS = {
    'ubuntu-19.10-desktop-amd64.iso': [
        'Tested in KVM, works (boots into live session)',
    ],
    'ubuntu-18.04.3-desktop-amd64.iso': [
        'Tested in KVM, works (boots into live session)',
    ],
    'ubuntu-18.04.3-live-server-amd64.iso': [
        "Tested in KVM, works (with some scary-looking weird messages during boot)",
        "(at least I get the installer; haven't tried to complete the installation)",
    ],
}

ENTRY = """
menuentry "{title}" {{
    # {test_status}
    set isofile="/ubuntu/{isofile}"
    loopback loop $isofile
    # {comment}
    linux (loop)/casper/vmlinuz iso-scan/filename=$isofile {cmdline}
    initrd (loop)/casper/initrd
}}

""".lstrip()

SUBMENU = """
submenu "{title} >" {{

{entries}

}} # end of submenu

"""

FOOTER = """
##submenu "Ubuntu 16.04 LTS >" {
##
##menuentry "Ubuntu 16.04.6 LTS (x86-64 server) DOES NOT WORK" {
##    # Tested in KVM, boots and then fails to find the CD-ROM
##    set isofile="/ubuntu/ubuntu-16.04.6-server-amd64.iso"
##    loopback loop $isofile
##    linux (loop)/install/vmlinuz iso-scan/filename=$isofile file=/cdrom/preseed/ubuntu-server.seed quiet ---
##    initrd (loop)/install/initrd.gz
##}
##
##menuentry "Ubuntu 16.04.6 LTS (x86-64 server, HWE kernel) DOES NOT WORK" {
##    # Tested in KVM, boots and then fails to find the CD-ROM
##    set isofile="/ubuntu/ubuntu-16.04.6-server-amd64.iso"
##    loopback loop $isofile
##    linux (loop)/install/hwe-vmlinuz iso-scan/filename=$isofile file=/cdrom/preseed/hwe-ubuntu-server.seed quiet ---
##    initrd (loop)/install/hwe-initrd.gz
##}
##
##} # end of submenu


##submenu "Firmware upgrade images >" {
##
##menuentry "Lenovo ThinkPad X200 BIOS update bootable CD (version 3.21)" {
##    # Works!
##    # See also: /boot/x200-bios/*.iso
##    # See also: http://www.donarmstrong.com/posts/x200_bios_update/
##    set memdisk="/boot/syslinux-memdisk"
##    set imgfile="/boot/lenovo-thinkpad-x200-bios.img"
##    linux16 $memdisk
##    initrd16 $imgfile
##}
##
##menuentry "Lenovo ThinkPad X200 BIOS update bootable CD (version 3.21) - alternative boot method" {
##    # Not tested
##    set memdisk="/boot/syslinux-memdisk"
##    set isofile="/boot/x200-bios/6duj46uc.iso"
##    linux16 $memdisk iso
##    initrd16 $isofile
##}
##
##menuentry "Intel SSD firmware update (version 1.92)" {
##    set memdisk="/boot/syslinux-memdisk"
##    set imgfile="/boot/intel-ssd-firmware.img"
##    linux16 $memdisk
##    initrd16 $imgfile
##}
##
##} # end of submenu

menuentry "Memory test (memtest86+)" {
    linux16 /boot/memtest86+.bin
}
"""


def make_grub_cfg():
    return (
        HEADER
        + mkentry('ubuntu-19.10-desktop-amd64.iso')
        + mksubmenu('Ubuntu 18.04 LTS', [
            mkentry('ubuntu-18.04.3-desktop-amd64.iso'),
            mkentry('ubuntu-18.04.3-live-server-amd64.iso'),
        ])
        + FOOTER
    )


def mksubmenu(title, entries):
    return SUBMENU.format(
        title=title,
        entries=''.join(entries).rstrip(),
    )


def mkentry(isofile):
    return ENTRY.format(
        isofile=isofile,
        title=mktitle(isofile),
        test_status=mkteststatus(isofile),
        comment=mkcomment(isofile),
        cmdline=mkcmdline(isofile),
    ).replace('\n    # \n', '\n')  # remove empty comments


def mktitle(isofile):
    # ubuntu-XX.XX-variant-arch.iso
    ubuntu, release, rest = isofile.rpartition('.')[0].split('-', 2)
    variant, arch = rest.rsplit('-', 1)
    if is_lts(release):
        release += ' LTS'
    return f'Ubuntu {release} ({ARCHS.get(arch, arch)} {VARIANTS.get(variant, variant)})'


def mkteststatus(isofile):
    return '\n    # '.join(TEST_STATUS.get(isofile, 'Untested'))


def mkcomment(isofile):
    if '-desktop-' in isofile:
        return 'NB: add only-ubiquity to kernel command line prior to --- to launch just the installer'
    return ''


def mkcmdline(isofile):
    if '-desktop-' in isofile:
        return 'file=/cdrom/preseed/ubuntu.seed boot=casper quiet splash ---'
    if '-live-server-' in isofile:
        return 'boot=casper quiet ---'
    return '---'


def is_lts(release):
    major, minor = map(int, release.split('.')[:2])
    # 6.06 was the first LTS release; since then there's been an LTS every two
    # years: 8.04, 10.04, 12.04, 14.04, 16.04, 18.04 and 20.04.
    # we can ignore the past and focus on the current pattern.
    return major % 2 == 0 and minor == 4


def main():
    print(make_grub_cfg(), end="")


if __name__ == "__main__":
    main()
