Bootable USB disk that lets you choose an ISO image
===================================================

This is basically a newer iteration on
https://mg.pov.lt/blog/booting-iso-from-usb.html

Creating a bootable USB disk that lets you boot any Ubuntu ISO image:

1. Mount a USB disk with a sufficient amount of free space.  Note the device
   name (e.g. `/dev/sdb`) and the mount point (e.g. `/media/mg/MG-FLASH`).

2. Install GRUB:

    ```
    sudo grub-install --target=i386-pc \
                      --root-directory=/media/mg/MG-FLASH /dev/sdb
    ```

   (you may have to also use `--force`)

3. Perhaps also install an UEFI bootloader

    ```
    sudo grub-install --target=x86_64-efi --removable \
                      --root-directory=/media/mg/MG-FLASH \
                      --efi-directory=/media/mg/MG-FLASH /dev/sdb
    ```

4. Download Ubuntu ISO images you want

    ```
    cd /media/mg/MG-FLASH
    git clone https://github.com/mgedmin/ubuntu-images ubuntu
    cd ubuntu
    # maybe edit the Makefile to pick what Ubuntu versions and variants you want
    make verify-all
    ```

5. Check out this repository (this is tricky because git doesn't want to check
   out things into an existing non-empty directory)

    ```
    git clone https://github.com/mgedmin/bootable-iso /tmp/bootable-iso
    mv /tmp/bootable-iso/.git /media/mg/MG-FLASH/boot/grub/
    mv /tmp/bootable-iso/* /media/mg/MG-FLASH/boot/grub/
    ```

6. Run `make -C /media/mg/MG-FLASH/boot/grub/` to build a `grub.cfg` that
   matches your Ubuntu images

7. Test that things work


Testing with KVM
----------------

1. Find the device name

    ```
    udisksctl status
    ```

2. Unmount the device

    ```
    udisksctl unmount -b /dev/sdb1
    ```

3. Boot it in KVM

    ```
    sudo setfacl -m user:$USER:rw /dev/sdb
    kvm -m 2048 -k en-us -drive format=raw,file=/dev/sdb
    ```

4. When you're done testing, mount the device again with

    ```
    udisksctl mount -b /dev/sdb1
    ```


Adding new boot menu entries
----------------------------

1. Edit `mkgrubcfg.py`.
2. Find the `KNOWN_COMMAND_LINES` mapping.
3. Run `python3 parseiso.py path/to/your/image.iso` to see the grub.cfg
4. Copy the kernel command-line arguments

For example,

```
$ python3 parseiso.py ../../ubuntu/ubuntu-20.04-desktop-amd64.iso
if loadfont /boot/grub/font.pf2 ; then
	set gfxmode=auto
	insmod efi_gop
	insmod efi_uga
	insmod gfxterm
	terminal_output gfxterm
fi

set menu_color_normal=white/black
set menu_color_highlight=black/light-gray

set timeout=5
menuentry "Ubuntu" {
	set gfxpayload=keep
	linux	/casper/vmlinuz  file=/cdrom/preseed/ubuntu.seed maybe-ubiquity quiet splash ---
	initrd	/casper/initrd
}
menuentry "Ubuntu (safe graphics)" {
	set gfxpayload=keep
	linux	/casper/vmlinuz  file=/cdrom/preseed/ubuntu.seed maybe-ubiquity quiet splash nomodeset ---
	initrd	/casper/initrd
}
menuentry "OEM install (for manufacturers)" {
	set gfxpayload=keep
	linux	/casper/vmlinuz  file=/cdrom/preseed/ubuntu.seed only-ubiquity quiet splash oem-config/enable=true ---
	initrd	/casper/initrd
}
grub_platform
if [ "$grub_platform" = "efi" ]; then
menuentry 'Boot from next volume' {
	exit
}
menuentry 'UEFI Firmware Settings' {
	fwsetup
}
fi
```

Find the main menu entry

```
menuentry "Ubuntu" {
	set gfxpayload=keep
	linux	/casper/vmlinuz  file=/cdrom/preseed/ubuntu.seed maybe-ubiquity quiet splash ---
	initrd	/casper/initrd
}
```

Look at the `linux` line

```
	linux	/casper/vmlinuz  file=/cdrom/preseed/ubuntu.seed maybe-ubiquity quiet splash ---
```

Convert it to `KNOWN_COMMAND_LINES` in mkgrubcfg.py

```
KNOWN_COMMAND_LINES = {
    ...
    'ubuntu-20.04-desktop-amd64.iso': 'file=/cdrom/preseed/ubuntu.seed maybe-ubiquity quiet splash ---',
    ...
}
```
