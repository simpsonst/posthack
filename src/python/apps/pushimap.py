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
import os
import sys
import email
import getopt
from pprint import pprint

from config import PosthackConfiguration

if __name__ == '__main__':
    ## Get configuration.
    cfg_name = None
    acc_name = None
    mb_name = 'INBOX'
    flags = []
    opts, args = getopt.getopt(sys.argv[1:], "f:a:d:sF")
    for opt, val in opts:
        if opt == '-f':
            cfg_name = val
        elif opt == '-a':
            acc_name = val
        elif opt == '-d':
            mb_name = val
        elif opt == '-s':
            flags.append('\Seen')
        elif opt == '-F':
            flags.append('\Flagged')
            pass
        continue
    config = PosthackConfiguration(cfg_name, acc_name)
    if len(args) == 0:
        args.append('/dev/stdin')
        pass

    ## Get account details and open the connection.
    acc, conn = config.open_account()

    try:
        ## Add configured flags.
        for tconf in acc.get('tags', []):
            ## Skip entries that don't define a tag.
            tnam = tconf.get('name', None)
            if tnam is None:
                continue

            ## Skip entries that require a non-empty environment
            ## variable.
            tenv = tconf.get('env', None)
            if tenv is not None and len(os.environ.get(tenv, '')) == 0:
                continue

            ## Add this tag.
            flags.append(tnam)
            continue

        ## Process the plain arguments as filenames.
        for fn in args:
            if fn is None or fn == '':
                continue

            ## Read in the message.
            with open(fn, "rb") as fp:
                msg = email.message_from_binary_file(fp)
                pass

            ## Attempt to add the file's contents as a message, or
            ## create the folder and try again.
            created = False
            while True:
                idate = imaplib.Time2Internaldate(time.time())
                typ, erk = conn.append('"' + mb_name + '"',
                                       ' '.join(flags), idate,
                                       msg.as_bytes(unixfrom=True))
                if typ != 'NO':
                    sys.exit()
                    pass
                if created:
                    sys.exit(1)
                    pass
                typ, erk = conn.create(mb_name)
                created = True
                continue
            continue
        pass
    finally:
        conn.logout()
        pass
    pass
