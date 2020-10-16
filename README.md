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

   (be very careful not to forget `--removable`, or it'll overwrite your EFI
   boot variables and your host machine will fail to boot!)

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

2. Run

    ```
    sh kvmboot /dev/sdb1
    ```

3. Record the test results in mkgrubcfg.py


Other resources
---------------

- https://help.ubuntu.com/community/Grub2/ISOBoot
