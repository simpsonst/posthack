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

"""Unpack a MIME message onto STDOUT."""

import sys
import email
import re
from getopt import getopt

if __name__ == '__main__':
    msg = email.message_from_binary_file(sys.stdin.buffer)
    ifmt = re.compile(r'^[0-9]+$')
    mfmt = re.compile(r'^\w+/[-.\w]+(?:\+[-.\w]+)?$')
    path = 0
    args = sys.argv[1:]
    if len(args) == 0:
        args = [ '-s', '1' ]
        pass
    while len(args) > 0:
        opts, args = getopt(args, "s:t:d:n:")
        ct = re.compile('.*')
        cd = None
        nm = None
        skip = 0
        for opt, val in opts:
            if opt == '-s':
                skip = int(val)
                pass
            elif opt == '-t':
                ct = re.compile('^' + re.escape(val) + '$')
                pass
            elif opt == '-d':
                cd = re.compile('^' + re.escape(val) + '$')
                pass
            elif opt == '-n':
                nm = re.compile('^' + re.escape(val) + '$')
                pass
            continue
        path += 1

        if not msg.is_multipart():
            sys.stderr.write('Not multipart at %d\n' % path)
            sys.exit(1)
            pass

        i = 0
        for part in msg.get_payload():
            i += 1
            if not ct.match(part.get_content_type()):
                continue
            cdv = part.get_content_disposition()
            if cd is not None:
                if cdv is None or not cd.match(cdv):
                    continue
                pass
            if nm is not None:
                par = part.get_param('name', header='Content-Disposition')
                if cdv is None or par is None or not nm.match(par):
                    continue
                pass
            if skip > 0:
                skip -= 1
                continue
            msg = part
            break
        
    sys.stdout.buffer.write(msg.get_payload(0).as_bytes(unixfrom=True))
    pass
