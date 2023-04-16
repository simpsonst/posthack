## Copyright (c) 2022, Lancaster University
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

import os
import sys
import email.message
import email
import re
import base64
import quopri
import yaml
from getopt import getopt
from pprint import pprint

import config

def strip_lines(lines, blocks):
    lim = int((len(lines) + 1) / 2)
    for i in range(0, lim):
        for cand in blocks:
            if i + len(cand) > len(lines):
                continue
            okay = True
            clen = len(cand)
            for j in range(0, clen):
                if cand[j] != lines[(i + j) * 2]:
                    okay = False
                    break
                continue
            if not okay:
                continue
            del lines[2 * i: 2 * (i + clen)]
            return True
        continue
    return False

if __name__ == '__main__':
    cfg_file = None
    acc_name = None
    opts, args = getopt(sys.argv[1:], "f:a:")
    for opt, val in opts:
        if opt == '-f':
            cfg_file = val
        elif opt == '-a':
            acc_name = val
            pass
        continue
    conf = config.PosthackConfiguration(cfg_file, acc_name)
    blocks = conf.get_blocks()

    crlf = re.compile(r'(\r?\n)')

    ## Process the message.
    msg = email.message_from_binary_file(sys.stdin.buffer)
    for part in msg.walk():
        ## TODO: Handle text/calendar too.
        if part.get_content_type() == 'text/plain' or \
           part.get_content_type() == 'text/html':
            ## Get the content as a string.
            cs = part.get_content_charset('us-ascii')
            tenc = part.get('Content-Transfer-Encoding')
            text = part.get_payload(decode=True)
            text = text.decode(cs)

            ## Split the content by lines, preserving the line
            ## terminators.  'lines' alternately contains a line
            ## followed by its terminator.  An odd number of entries
            ## indicates that the last line wasn't terminated.
            lines = crlf.split(text)

            ## Remove sequences of lines matching those loaded from
            ## configuration.  The following terminators are also
            ## deleted.
            strip_lines(lines, blocks)

            ## Join all the remaining lines and their terminators back
            ## up again.
            text = ''.join(lines)

            ## Re-encode the text to its byte form.
            text = text.encode(cs)
            if tenc == 'base64':
                text = base64.b64encode(text)
            elif tenc == 'quoted-printable':
                text = quopri.encodestring(text)
                pass
            part.set_payload(text)
            pass
        continue
    sys.stdout.buffer.write(msg.as_bytes(unixfrom=True))
    pass
