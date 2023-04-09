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
    ## Parse arguments.
    cfg_name = os.environ['PUSHIMAP_CONFIG'] \
               if 'PUSHIMAP_CONFIG' in os.environ \
                  else os.path.expanduser('~/.config/posthack/pushimap.yml')
    acc_name = os.environ['PUSHIMAP_ACCOUNT'] \
               if 'PUSHIMAP_ACCOUNT' in os.environ \
                  else None
    msg_file = None
    mb_name = 'INBOX'
    flags = []
    action = "push"
    dry_run = False
    opts, args = getopt.getopt(sys.argv[1:], "f:a:d:sFlPn")
    for opt, val in opts:
        if opt == '-f':
            cfg_name = val
        elif opt == '-d':
            mb_name = val
        elif opt == '-a':
            acc_name = val
        elif opt == '-s':
            flags.append('\Seen')
        elif opt == '-F':
            flags.append('\Flagged')
        elif opt == '-l':
            action = "list"
        elif opt == '-P':
            action = "purge"
        elif opt == '-n':
            dry_run = True
            pass
        continue
    if len(args) == 0:
        args.append('/dev/stdin')
        pass

    ## Read the account details.
    with open(os.path.expanduser(cfg_name), "r") as stream:
        config = yaml.safe_load(stream)
        pass
    if acc_name is None:
        acc_name = config.get('default-account', 'default')
        pass
    accounts = { }
    pwf_name = config.get('secrets', '~/.config/posthack/secrets.yml')
    with open(os.path.expanduser(pwf_name), "r") as stream:
        passwords = yaml.safe_load(stream)
        pass
    for acc in config['accounts'] or []:
        if 'name' not in acc:
            continue
        entry = accounts.setdefault(acc['name'], { })
        opt_copy('hostname', entry, acc)
        opt_copy('username', entry, acc)
        opt_copy('port', entry, acc, xform=lambda x: int(x))
        opt_copy('password', entry, passwords, src_key=acc['name'])
        opt_copy('purge', entry, acc)
        opt_copy('tags', entry, acc)
        continue
    acc = accounts[acc_name]

    ## Connect to the server.
    hostname = acc['hostname']
    port = acc.get('port', 993)
    c = imaplib.IMAP4_SSL(hostname, port)
    try:
        ## Authenticate with the server.
        username = acc['username']
        password = acc['password']
        c.login(username, password)

        if action == "list":
            typ, dat = c.list()
            pprint(dat)
        elif action == "purge":
            print('Purging...')
            rpol = acc.get('purge', { })

            ## Identify the trash folder,
            typ, dat = c.list()
            trash = None
            for item in dat:
                fstxt, dlim, mbox = imap_list_fmt.match(item).groups()
                fs = fstxt.split()
                if '\Trash' in fs:
                    trash = mbox.strip('"')
                    break
                pass
            if trash is None:
                print('  No trash folder')
                pass
            else:
                # rsp = c.select(mailbox = trash)
                # pprint(rsp)

                ## Go through each 'purge' section, and apply deletions.
                for sect in rpol['purge'] or []:
                    folder = sect.get("folder")
                    if folder is None:
                        continue
                    print('\nFolder %s' % folder)
                    flags_txt = sect.get('flags')
                    flags = set() if flags_txt is None \
                        else set(flags_text.split())
                    (typ, cnt) = c.select(mailbox=folder)
                    if typ != "OK":
                        print('  Skipped - %s' % cnt[0])
                        continue

                    ## Apply a maximum age in days, if specified.
                    max_age_txt = sect.get("max-age")
                    if max_age_txt is not None:
                        max_age = int(max_age_txt)
                        if max_age < 1:
                            print('  Skipped - non-positive age')
                            continue

                        ## Identify old messages.
                        cut_off = datetime.datetime.now()
                        cut_off -= datetime.timedelta(days=max_age)
                        cut_off = cut_off.strftime("%d-%b-%Y")
                        print('  Deleting older than %s' % cut_off)
                        crit = 'BEFORE "%s"' % cut_off
                        if 'unread' not in flags:
                            crit = 'SEEN ' + crit
                            pass
                        #crit = 'UNDELETED ' + crit
                        if 'starred' not in flags:
                            crit = 'UNFLAGGED ' + crit
                            pass
                        crit = '(%s)' % crit
                        typ, mnums = c.search(None, crit)
                        if typ != 'OK':
                            print('    Search error: %s' % mnums)
                            continue
                        if mnums[0] == '':
                            print('    No matches')
                            continue

                        ## The message numbers are space-separated,
                        ## but we need them comma-separated to feed
                        ## them back to the server.
                        mnums = mnums[0].split(' ')
                        numlen = len(mnums)
                        mnums = ','.join(mnums)

                        ## Copy the selected messages to trash, mark
                        ## the originals as deleted, and expunge.
                        # print('into %s: %s' % (trash, mnums))
                        if not dry_run:
                            typ, rsp = c.copy(mnums, trash)
                            if typ != 'OK':
                                print('    Copy error: %s' % rsp)
                                continue
                            # pprint(rsp)
                            rsp = c.store(mnums, '+FLAGS', '\Deleted')
                            # pprint(rsp)
                            rsp = c.expunge()
                            # pprint(rsp)
                            pass
                        print('    Moved %d to trash' % numlen)
                        pass

                    ## Apply a maximum number of the most recent
                    ## messages, if specified.
                    msg_lim_txt = sect.get("message-limit")
                    if msg_lim_txt is not None:
                        msg_lim = int(msg_lim_txt)
                        if msg_lim < 1:
                            print('  Skipped - non-positive message limit')
                            continue

                        ## Get all messages.  The most recent are at
                        ## the end.
                        print('  Retaining newest %d' % msg_lim)
                        #typ, mnums = c.search(None, 'ALL')
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
                        typ, mnums = c.sort('DATE', 'UTF-8', '(%s)' % crit)
                        if typ != 'OK':
                            print('    Search error: %s' % mnums)
                            continue
                        if mnums[0] == '':
                            print('    No matches')
                            continue

                        ## The message numbers are space-separated,
                        ## but we need them comma-separated to feed
                        ## them back to the server.
                        mnums = mnums[0].split(' ')
                        del mnums[-msg_lim:]
                        numlen = len(mnums)
                        if numlen < 1:
                            print('    Too few')
                            continue
                        mnums = ','.join(mnums)
                        print('    Will delete %s' % mnums)

                        ## Copy the selected messages to trash, mark
                        ## the originals as deleted, and expunge.
                        # print('into %s: %s' % (trash, mnums))
                        if not dry_run:
                            typ, rsp = c.copy(mnums, trash)
                            if typ != 'OK':
                                print('    Copy error: %s' % rsp)
                                continue
                            # pprint(rsp)
                            rsp = c.store(mnums, '+FLAGS', '\Deleted')
                            # pprint(rsp)
                            rsp = c.expunge()
                            # pprint(rsp)
                            pass
                        print('    Moved %d to trash' % numlen)
                        pass

                    c.select()
                    continue
                pass
            pass
        else:
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
                with open(fn, "r") as fp:
                    msg = email.message_from_file(fp)
                    pass

                ## Attempt to add the file's contents as a message, or
                ## create the folder and try again.
                created = False
                while True:
                    idate = imaplib.Time2Internaldate(time.time())
                    typ, erk = c.append(mb_name, ' '.join(flags), idate,
                                        msg.as_bytes(unixfrom=True))
                    if typ != 'NO':
                        sys.exit()
                        pass
                    if created:
                        sys.exit(1)
                        pass
                    typ, erk = c.create(mb_name)
                    created = True
                    continue
                continue
            pass
    finally:
        c.logout()
        pass
    pass

