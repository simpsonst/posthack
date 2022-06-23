all::

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
scripts += pushimap
scripts += remove-external-sender
scripts += remove-safelinks
scripts += strip-label
scripts += unpack-email

BINODEPS_SHAREDIR=src/share
BINODEPS_SCRIPTDIR=$(BINODEPS_SHAREDIR)
SHAREDIR ?= $(PREFIX)/share/posthack
LIBEXECDIR ?= $(PREFIX)/libexec/posthack
include binodeps.mk

install:: install-hidden-scripts
