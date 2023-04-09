all::

FIND=find
PREFIX=/usr/local

## Provide a version of $(abspath) that can cope with spaces in the
## current directory.
myblank:=
myspace:=$(myblank) $(myblank)
MYCURDIR:=$(subst $(myspace),\$(myspace),$(CURDIR)/)
MYABSPATH=$(foreach f,$1,$(if $(patsubst /%,,$f),$(MYCURDIR)$f,$f))

-include posthack-env.mk
-include $(call MYABSPATH,config.mk)

scripts += decode-header
scripts += push-imap
hidden_scripts += purge-imap
scripts += remove-external-sender
scripts += remove-safelinks
scripts += strip-label
scripts += unpack-email

BINODEPS_SHAREDIR=src/share
BINODEPS_SCRIPTDIR=$(BINODEPS_SHAREDIR)
SHAREDIR ?= $(PREFIX)/share/posthack
LIBEXECDIR ?= $(PREFIX)/libexec/posthack

python3_zips += apps

include binodeps.mk
include pynodeps.mk

all:: python-zips
install:: install-python-zips
install:: install-scripts
install:: install-hidden-scripts

tidy::
	$(FIND) . -name "*~" -delete
