SHELL = /bin/bash


grub.cfg: mkgrubcfg.py ../../ubuntu ../../ubuntu/*.iso
	python3 mkgrubcfg.py -o grub.cfg

diff:
	diff -u grub.cfg <(python3 mkgrubcfg.py)
