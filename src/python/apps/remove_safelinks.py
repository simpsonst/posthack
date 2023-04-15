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
import urllib
import base64
import quopri
from bs4 import BeautifulSoup
#from mimeparse import parse_mime_type

def decode_text(text):
    unreserved = r'[-A-Za-z0-9._~]'
    pctenc = r'%[0-9a-fA-F]{2}'
    subdel = '[!$&\'()*+,;=]'
    regname = r'(?:%s|%s|%s)*' % (unreserved, pctenc, subdel)
    decoct = r'(?:[0-9]|[1-9][0-9]|[1-9][0-9][0-9]|2[0-4][0-9]|25[0-5])'
    ipv4 = r'%s\.%s\.%s\.%s' % (decoct, decoct, decoct, decoct)
    ipfut = r'v[0-9a-fA-F]+\.(?:%s|%s|:)+' % (unreserved, subdel)
    ipv6 = r'[0-9a-fA-F:]+'
    iplit = r'\[(?:%s|%s)\]' % (ipv6, ipfut)
    host = r'(?:%s|%s|%s)' % (iplit, ipv4, regname)
    port = r'(?:[0-9]*)'
    scheme = r'(?:[A-Za-z][A-Za-z0-9]*)'
    user = r'(?:%s|%s|%s|:)*' % (unreserved, pctenc, subdel)
    auth = r'(?:(%s)@)?(%s)(?::(%s))?' % (user, host, port)
    path = r'(?:/(?:%s|%s|%s|[:@])*)*' % (unreserved, pctenc, subdel)
    hierpart = r'//(%s)(%s)' % (auth, path)
    query = r'(?:%s|%s|%s|[:@/?])*' % (unreserved, pctenc, subdel)
    url = r'(%s):(%s)(?:\?(%s))?(?:#(%s))?' % (scheme, hierpart, query, query)
    ptn = re.compile(url)

    last = 0
    res = ""
    for m in re.finditer(ptn, text):
        # print m.start(), m.end()
        # if m.group(1) is not None: print 'scheme ' + m.group(1)
        # if m.group(2) is not None: print 'hierpart ' + m.group(2)
        # if m.group(3) is not None: print 'auth ' + m.group(3)
        # if m.group(4) is not None: print 'user ' + m.group(4)
        # if m.group(5) is not None: print 'host ' + m.group(5)
        # if m.group(6) is not None: print 'port ' + m.group(6)
        # if m.group(7) is not None: print 'path ' + m.group(7)
        # if m.group(8) is not None: print 'query ' + m.group(8)
        # if m.group(9) is not None: print 'fragment ' + m.group(9)
        res += text[last:m.start()]
        qs = m.group(8)
        hostname = m.group(5)
        if qs is not None and \
           hostname.lower().endswith('.safelinks.protection.outlook.com'):
            qdict = urllib.parse.parse_qs(m.group(8))
            if 'url' in qdict:
                alt = qdict['url'][0]
                res += alt
                # print 'Replacement: ' + alt
            else:
                res += m.group()
                pass
        else:
            res += m.group()
            pass
        last = m.end()
        continue
    res += text[last:]
    return res

if __name__ == '__main__':
    msg = email.message_from_file(sys.stdin)
    for part in msg.walk():
        #print [method_name for method_name in dir(part) if callable(getattr(part, method_name))]
        if part.get_content_type() == 'text/plain':
            cs = part.get_content_charset('us-ascii')
            tenc = part.get('Content-Transfer-Encoding')
            text = part.get_payload(decode=True)
            text = text.decode(cs)
            text = decode_text(text)
            text = text.encode(cs)
            if tenc == 'base64':
                text = base64.b64encode(text)
            elif tenc == 'quoted-printable':
                text = quopri.encodestring(text)
                pass
            part.set_payload(text)
        elif part.get_content_type() == 'text/html':
            cs = part.get_content_charset('us-ascii')
            tenc = part.get('Content-Transfer-Encoding')
            text = part.get_payload(decode=True)
            # if cs is not None:
            #     text = text.decode(cs)
            soup = BeautifulSoup(text, 'html.parser', from_encoding=cs)
            for link in soup.find_all('a'):
                val = link.get('href')
                if val is None:
                    continue
                #print 'Was: %s' % val
                val = decode_text(val)
                #print 'Now: %s' % val
                link['href'] = val
                continue
            text = soup.encode(cs)
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
