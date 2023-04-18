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

import sys
import email
import re
from email.header import decode_header

if __name__ == '__main__':
    msg = email.message_from_binary_file(sys.stdin.buffer)
    default_charset = 'ASCII'
    oldsubj = ''.join([ txt.decode(enc or default_charset)
                        if isinstance(txt, bytes) else txt
                        for txt, enc in decode_header(msg['Subject']) ])
    msg['X-Old-Subject'] = msg['Subject']

    subj = oldsubj
    for word in sys.argv[1:]:
        ptn = re.compile(r'(^|\s+)(' + re.escape(word) + r')(?:\s*|$)')
        last = 0
        subj = ''
        for m in re.finditer(ptn, oldsubj):
            subj += oldsubj[last:m.start()]
            subj += m.group(1)
            last = m.end()
            continue
        subj += oldsubj[last:]
        oldsubj = subj
        continue

    del msg['Subject']
    msg['Subject'] = subj
    sys.stdout.buffer.write(msg.as_bytes(unixfrom=True))
    pass
