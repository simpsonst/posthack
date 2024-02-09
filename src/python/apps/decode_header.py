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

import re
import sys
from email.header import decode_header
nvpat = re.compile(r"(?:([^:]+):)?(.*)", re.DOTALL | re.MULTILINE)
crlffold = re.compile(r'\s+', re.DOTALL | re.MULTILINE)
default_charset = 'US-ASCII'

raw = sys.stdin.buffer.read()
# print(repr(raw))
mt = nvpat.match(str(raw, 'US-ASCII'))
name = mt.group(1)
if name is not None:
    name = name.strip()
    pass
value = crlffold.sub(r' ', mt.group(2)).strip()
# print(repr(value))

dh = decode_header(value)
# print(repr(dh))
res = '' if name is None else (name + ": ")
gap = False
first = True
for data, cs in dh:
    if isinstance(data, str):
        # if not first:
        #     res += ' '
        #     pass
        res += data
        #.strip()
        gap = True
    elif cs is None:
        # if not first:
        #     res += ' '
        #     pass
        res += str(data, default_charset)
        #.strip()
        gap = True
    else:
        # if gap and not first:
        #     res += ' '
        #     pass
        res += str(data, cs)
        gap = False
        pass
    first = False
    continue
print(res)
