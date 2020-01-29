Bootable USB disk that lets you choose an ISO image
===================================================

This is basically a newer iteration on
https://mg.pov.lt/blog/booting-iso-from-usb.html

Creating a bootable USB disk that lets you boot any Ubuntu ISO image:

#. Mount a USB disk with a sufficient amount of free space.  Note the device
   name (e.g. `/dev/sdb`) and the mount point (e.g. `/media/mg/MG-FLASH`).

#. Install GRUB:

    ```
    sudo grub-install --target=i386-pc \
                      --root-directory=/media/mg/MG-FLASH /dev/sdb
    ```

   (you may have to also use `--force`)

#. Perhaps also install an UEFI bootloader

    ```
    sudo grub-install --target=x86_64-efi --removable \
                      --root-directory=/media/mg/MG-FLASH \
                      --efi-directory=/media/mg/MG-FLASH /dev/sdb
    ```

#. Download Ubuntu ISO images you want

    ```
    cd /media/mg/MG-FLASH
    git clone https://github.com/mgedmin/ubuntu-images ubuntu
    cd ubuntu
    make verify-all
    ```

#. Check out this repository (this is tricky because git doesn't want to check
   out things into an existing non-empty directory)

    ```
    git clone https://github.com/mgedmin/bootable-iso /tmp/bootable-iso
    mv /tmp/bootable-iso/.git /media/mg/MG-FLASH/boot/grub/
    mv /tmp/bootable-iso/* /media/mg/MG-FLASH/boot/grub/
    ```

#. Edit `/media/mg/MG-FLASH/boot/grub/grub.cfg` so it matches your Ubuntu images

#. Test that things work


Testing with KVM
----------------

#. Unmount the device

    ```
    udisksctl unmount -b /dev/sdb1
    ```

#. Boot it in KVM

    ```
    sudo setfacl -m user:$USER:rw /dev/sdb
    kvm -m 2048 -k en-us -drive format=raw,file=/dev/sdb
    ```

#. When you're done testing, mount the device again with

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
7. Add `iso-scan/filename=$isofile` on the kernel command line,
   before `--` or `---`.  (This works for images using casper, i.e. Ubuntu
   desktop and live-server ISOs.  Server ISOs that use debian-installer don't
   actually work at all booted through grub's loopback.)
