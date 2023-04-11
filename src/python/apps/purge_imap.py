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

import sys
import getopt
import re
import datetime
from pprint import pprint
from config import PosthackConfiguration

if __name__ == '__main__':
    ## Get configuration.
    cfg_name = None
    acc_name = None
    dry_run = False
    opts, args = getopt.getopt(sys.argv[1:], "f:a:n")
    for opt, val in opts:
        if opt == '-f':
            cfg_name = val
        elif opt == '-a':
            acc_name = val
        elif opt == '-n':
            dry_run = True
            pass
        continue
    config = PosthackConfiguration(cfg_name, acc_name)

    ## Get account details and open the connection.
    acc, conn = config.open_account()

    try:
        ## Identify the trash folder,
        imap_list_fmt = \
            re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
        typ, dat = conn.list()
        trash = None
        for item in dat:
            fstxt, dlim, mbox = \
                imap_list_fmt.match(item.decode('US-ASCII')).groups()
            fs = fstxt.split()
            if '\Trash' in fs:
                trash = mbox.strip('"')
                break
            pass
        else:
            sys.stderr.write('no trash folder\n')
            sys.exit(1)
            pass

        ## Go through each 'purge' section, and apply deletions.
        for sect in acc.get('purge', [ ]):
            folder = sect.get("folder")
            if folder is None:
                continue
            sys.stderr.write('Folder %s\n' % folder)
            flags_txt = sect.get('flags')
            flags = set() if flags_txt is None \
                else set(flags_text.split())
            (typ, cnt) = conn.select(mailbox='"' + folder + '"')
            if typ != "OK":
                sys.stderr.write('  Skipped - %s\n' % cnt[0])
                continue

            ## Apply a maximum age in days, if specified.
            max_age_txt = sect.get("max-age")
            if max_age_txt is not None:
                max_age = int(max_age_txt)
                if max_age < 1:
                    sys.stderr.write('  Skipped - non-positive age\n')
                    continue

                ## Identify old messages.
                cut_off = datetime.datetime.now()
                cut_off -= datetime.timedelta(days=max_age)
                cut_off = cut_off.strftime("%d-%b-%Y")
                sys.stderr.write('  Deleting older than %s\n' % cut_off)
                crit = 'BEFORE "%s"' % cut_off
                if 'unread' not in flags:
                    crit = 'SEEN ' + crit
                    pass
                #crit = 'UNDELETED ' + crit
                if 'starred' not in flags:
                    crit = 'UNFLAGGED ' + crit
                    pass
                crit = '(%s)' % crit
                typ, mnums = conn.search(None, crit)
                if typ != 'OK':
                    sys.stderr.write('    Search error: %s\n' % mnums)
                    continue
                mnums = mnums[0].decode('US-ASCII')
                if mnums == '':
                    sys.stderr.write('    No matches\n')
                    continue

                ## The message numbers are space-separated, but we
                ## need them comma-separated to feed them back to the
                ## server.
                mnums = mnums.split(' ')
                numlen = len(mnums)
                mnums = ','.join(mnums)

                ## Copy the selected messages to trash, mark the
                ## originals as deleted, and expunge.
                # print('into %s: %s' % (trash, mnums))
                if not dry_run:
                    typ, rsp = conn.copy(mnums, trash)
                    if typ != 'OK':
                        sys.stderr.write('    Copy error: %s\n' % rsp)
                        continue
                    # pprint(rsp)
                    rsp = conn.store(mnums, '+FLAGS', '\Deleted')
                    # pprint(rsp)
                    rsp = conn.expunge()
                    # pprint(rsp)
                    pass
                sys.stderr.write('    Moved %d to trash\n' % numlen)
                pass

            ## Apply a maximum number of the most recent messages, if
            ## specified.
            msg_lim_txt = sect.get("message-limit")
            if msg_lim_txt is not None:
                msg_lim = int(msg_lim_txt)
                if msg_lim < 1:
                    sys.stderr.write('  Skipped - non-positive message limit\n')
                    continue

                ## Get all messages.  The most recent are at the end.
                sys.stderr.write('  Retaining newest %d\n' % msg_lim)
                #typ, mnums = conn.search(None, 'ALL')
                crit = ''
                if 'unread' not in flags:
                    crit += ' SEEN'
                    pass
                if 'starred' not in flags:
                    crit += ' UNFLAGGED'
                    pass
                if crit == '':
                    crit = 'ALL'
                else:
                    crit = crit[1:]
                    pass
                typ, mnums = conn.sort('DATE', 'UTF-8', '(%s)' % crit)
                if typ != 'OK':
                    sys.stderr.write('    Search error: %s\n' % mnums)
                    continue
                mnums = mnums[0].decode('US-ASCII')
                if mnums == '':
                    sys.stderr.write('    No matches\n')
                    continue

                ## The message numbers are space-separated, but we
                ## need them comma-separated to feed them back to the
                ## server.
                mnums = mnums.split(' ')
                del mnums[-msg_lim:]
                numlen = len(mnums)
                if numlen < 1:
                    sys.stderr.write('    Too few\n')
                    continue
                mnums = ','.join(mnums)
                sys.stderr.write('    Will delete %s\n' % mnums)

                ## Copy the selected messages to trash, mark the
                ## originals as deleted, and expunge.
                # print('into %s: %s' % (trash, mnums))
                if not dry_run:
                    typ, rsp = conn.copy(mnums, trash)
                    if typ != 'OK':
                        sys.stderr.write('    Copy error: %s\n' % rsp)
                        continue
                    # pprint(rsp)
                    rsp = conn.store(mnums, '+FLAGS', '\Deleted')
                    # pprint(rsp)
                    rsp = conn.expunge()
                    # pprint(rsp)
                    pass
                sys.stderr.write('    Moved %d to trash\n' % numlen)
                pass
        
            conn.select()
            continue
        pass
    finally:
        conn.logout()
        pass
    pass
