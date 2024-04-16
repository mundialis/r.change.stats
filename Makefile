MODULE_TOPDIR = ../..

PGM = r.change.stats

include $(MODULE_TOPDIR)/include/Make/Script.make

python-requirements:
	pip install -r requirements.txt

default: python-requirements script
