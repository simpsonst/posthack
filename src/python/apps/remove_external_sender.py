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

def strip_lines(lines, blocks):
    for i in range(0, len(lines)):
        for cand in blocks:
            if i + len(cand) > len(lines):
                continue
            okay = True
            for j in range(0, len(cand)):
                if cand[j] != lines[i + j]:
                    okay = False
                    break
                continue
            if not okay:
                continue
            del lines[i:i + len(cand)]
            return True
        continue
    return False

if __name__ == '__main__':
    cfg_file = None
    opts, args = getopt(sys.argv[1:], "f:")
    for opt, val in opts:
        if opt == '-f':
            cfg_file = val
            pass
        continue
    if cfg_file is None:
        sys.stderr.write('Specify -f conf.yml\n')
        sys.exit(1)
        pass
    with open(os.path.expanduser(cfg_file), "r") as fp:
        config = yaml.safe_load(fp)
        pass
    blocks = []
    for text in config['blocks']:
        lines = text.splitlines()
        blocks.append(lines)
        continue

    ## Process the message.
    msg = email.message_from_file(sys.stdin)
    for part in msg.walk():
        if part.get_content_type() == 'text/plain' or \
           part.get_content_type() == 'text/html':
            # cs = part.get_content_charset('us-ascii')
            tenc = part.get('Content-Transfer-Encoding')
            text = part.get_payload(decode=True)
            # if cs is not None:
            #     text = text.decode(cs)
            lines = text.splitlines()
            strip_lines(lines, config['blocks'])
            text = '\n'.join(lines) + '\n'
            # if cs is not None:
            #     text = text.encode(cs)
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
