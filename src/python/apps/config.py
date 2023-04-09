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

import yaml
import os

def _opt_copy(dst_key, dst, src, src_key=None, xform=None):
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

class PosthackConfiguration:
    CONFIG_ENV = 'POSTHACK_CONFIG'
    ACCOUNT_ENV = 'POSTHACK_ACCOUNT'
    DEFAULT_CONFIG = '~/.config/posthack/config.yml'
    DEFAULT_SECRETS = '~/.config/posthack/secrets.yml'

    def __init__(self, _cfg_filename=None, account_name=None):
        if _cfg_filename is not None:
            self._cfg_filename = _cfg_filename
            pass
        else:
            self._cfg_filename = os.environ.get(self.CONFIG_ENV, None)
            if self._cfg_filename is None:
                self._cfg_filename = os.path.expanduser(self.DEFAULT_CONFIG)
                pass
            pass
            
        if account_name is not None:
            self.account_name = account_name
            pass
        else:
            self.account_name = os.environ.get(self.ACCOUNT_ENV, 'default')
            pass

        ## Load the configuration.
        with open(os.path.expanduser(self._cfg_filename), "r") as stream:
            config = yaml.safe_load(stream)
            pass

        ## Determine the default account.
        if self.account_name is None:
            self.account_name = config.get('default-account', 'default')
            pass

        ## Load in secrets.
        pwf_name = config.get('secrets', self.DEFAULT_SECRETS)
        with open(os.path.expanduser(pwf_name), "r") as stream:
            passwords = yaml.safe_load(stream)
            pass

        ## Merge account details.
        self.accounts = { }
        for acc in config.get('accounts', [ ]):
            if 'name' not in acc:
                continue
            entry = self.accounts.setdefault(acc['name'], { })
            _opt_copy('hostname', entry, acc)
            _opt_copy('username', entry, acc)
            _opt_copy('port', entry, acc, xform=lambda x: int(x))
            _opt_copy('password', entry, passwords, src_key=acc['name'])
            _opt_copy('purge', entry, acc)
            _opt_copy('tags', entry, acc)
            continue

        self.blocks = config.get('blocks', [ ])

        pass

    pass
