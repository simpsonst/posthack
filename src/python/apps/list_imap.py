## Copyright (c) 2023, Lancaster University
## All rights reserved.
##
## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions
## are met:
##
## 1. Redistributions of source code must retain the above copyright
##    notice, this list of conditions and the following disclaimer.
##
## 2. Redistributions in binary form must reproduce the above
##    copyright notice, this list of conditions and the following
##    disclaimer in the documentation and/or other materials provided
##    with the distribution.
##
## 3. Neither the name of the copyright holder nor the names of its
##    contributors may be used to endorse or promote products derived
##    from this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
## FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
## COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
## INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
## (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
## SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
## HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
## STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
## ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
## OF THE POSSIBILITY OF SUCH DAMAGE.

import imaplib
import time
import yaml
import os
import sys
import email.message
import email
import datetime
import re
import getopt
from pprint import pprint

from config import PosthackConfiguration

imap_list_fmt = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')

def opt_copy(dst_key, dst, src, src_key=None, xform=None):
    if dst_key in dst:
        return dst[dst_key]
    if src_key is None:
        src_key = dst_key
        pass
    if src_key not in src:
        return None
    val = src[src_key]
    if xform is not None:
        val = xform(val)
        pass
    ## TODO: Merge?
    dst[dst_key] = val
    return val

if __name__ == '__main__':
    ## Get configuration.
    cfg_name = None
    acc_name = None
    opts, args = getopt.getopt(sys.argv[1:], "f:a:")
    for opt, val in opts:
        if opt == '-f':
            cfg_name = val
        elif opt == '-a':
            acc_name = val
            pass
        continue
    config = PosthackConfiguration(cfg_name, acc_name)

    ## Get account details and open the connection.
    acc, conn = config.open_account()

    try:
        typ, dat = conn.list()
        pprint(dat)
    finally:
        conn.logout()
        pass

    pass

