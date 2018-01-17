Bootable USB disk that lets you choose an ISO image
===================================================

This is basically a newer iteration on
https://mg.pov.lt/blog/booting-iso-from-usb.html

Creating a bootable USB disk that lets you boot any Ubuntu ISO image:

1. Mount a USB disk with a sufficient amount of free space.  Note the device
   name (e.g. `/dev/sdb`) and the mount point (e.g. `/media/mg/MG-FLASH`).

1. Install GRUB:

    ```
    sudo grub-install --root-directory=/media/mg/MG-FLASH /dev/sdb
    ```

   (you may have to also use `--force`)

2. Download Ubuntu ISO images you want

    ```
    cd /media/mg/MG-FLASH
    git clone https://github.com/mgedmin/ubuntu-images ubuntu
    cd ubuntu
    make verify-all
    ```

3. Check out this repository (this is tricky because git doesn't want to check
   out things into an existing non-empty directory)

    ```
    git clone https://github.com/mgedmin/bootable-iso /tmp/
    mv /tmp/bootable-iso/.git /media/mg/MG-FLASH/boot/grub/
    mv /tmp/bootable-iso/* /media/mg/MG-FLASH/boot/grub/
    ```

4. Edit `/media/mg/MG-FLASH/boot/grub/grub.cfg` so it matches your Ubuntu images

5. Test that things work


Testing with KVM
----------------

1. Unmount the device

    ```
    udisksctl unmount -b /dev/sdb1
    ```

2. Boot it in KVM

    ```
    sudo kvm -m 2048 -hdb /dev/sdb
    ```

   You need sudo to let KVM access the block device, and you need at least 2 GB
   of RAM.

3. When you're done testing, mount the device again with

    ```
    udisksctl mount -b /dev/sdb1
    ```

Adding new boot menu entries
----------------------------

1. Edit `grub.cfg`.
2. Copy an existing menu/submenu that is similar.
3. Change version numbers.
4. Launch `mc` (Midnight Commander), find the ISO image, press Enter to look
   inside.
5. Locate the `boot/grub/grub.cfg` file inside the ISO image.
6. Copy the kernel command-line arguments exactly.
7. For desktop ISO images add `iso-scan/filename=$isofile` on the kernel
   command line, before `--` or `---`.  For some reason server ISO images don't
   need this.
