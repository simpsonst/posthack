# Purpose

These Python scripts are intended for use mostly in `procmail` rules, and provide the following functionality:

- Match on `Subject`, even if encoded.

- Strip mailing-list `[tags]`.

- Unpack forwarded emails as attachments.

- Restore mangled 'safelinks'.

- Strip 'external' warnings.

- Deliver to IMAP folders, starred and/or marked as read.  (TODO: And with custom tags!)

- Purge old messages from IMAP servers.


## Dealing with encoded subjects

The subject of an email is held in a header field `Subject`, and so it's usually restricted to `US-ASCII` encoding.
Other encodings are possible by encoding them with the likes of `=?utf-8?q?caf=C3=A9?=`.
`procmail` presents such content as is, not decoded, making it difficult to detect certain patterns consistently if they happen to have been included in such an encoding.
Use `decode-header` to convert an encoded subject into UTF-8:

```
:0 h
* ^Subject:.*=\?
SUBJECT=| formail -cXSubject: | decode-header

:0 hE
SUBJECT=| formail -cXSubject:
```

(The second rule acts as an undecoded back-up, should the first fail.)

You can then use this to test against:

```
* SUBJECT ?? ^Subject:.*ACTION REQUIRED
```


## Stripping subject tags

Emails sent to lists often have tags prefixed to them, e.g., `[EDAS-CFP]` or `[modfoo]`, so you know they are being delivered to you as a member of the list.
They might also be added by your institution to indicate some processing or status of the message, such as `[External]` or `[SPAM]`.
In many cases, these conditions are also indicated by header fields that are not normally displayed to the user, such as `X-Spam-Status: YES` or `List-Id: <modfoo.example.org>`, so they are functionally redundant in conjunction with `procmail` rules that use these hidden fields to direct messages to dedicated folders.
Use `strip-label` to remove matching strings from the subject, along with any trailing white space:

```
:0 fhw
* ^List-Id:.*<modfoo\.example\.org>
| strip-label '[modfoo]'
```


## Unpacking emails as attachments

At some point, I had set up one dysfunctional email account to forward to another, but the forwarding was broken such that the `Message-Id` header field was destroyed and replaced by something less than useless.
This broke threading, as all the `In-Reply-To` and `References` fields referred to phantom ids.
I found I could avoid this by using the option to forward as an attachment, which maintained the integrity of the message.
Of course, it then needed unpacking at the other end, for which I used the following:

```
:0 fw
* ^From:.*<the-dodgy-account@example\.com>
* ^X-MS-Has-Attach: yes
* ^X-MS-Exchange-Inbox-Rules-Loop: the-dodgy-account@example\.com
| unpack-email
```

Arguments allow you to walk a multipart message hierarchy:

- `-s *num*` &ndash; Skip `num` parts of the current message.

- `-t *type*` &ndash; Skip parts not of content type `type`.

- `-d *disp*` &ndash; Skip parts not of content disposition `disp`.

- `-n *name*` &ndash; Skip parts without a content disposition name `name`.

- `--` &ndash; Select the first part matching the above criteria, and make it the current message.
  `-s`, `-t`, `-d` and `-n` are then reset, so new criteria can be specified for selecting within the new current message.

If no arguments are supplied, `-s 1` is assumed (for backward compatibility).

## Restoring 'safe' links

Sometimes, your email provider will add 'safelinks', i.e., it will scan the email for links, and replace the URL with another that embeds it but points to the domain `safelinks.protection.outlook.com`.
If you follow the link, you first go to this site, which performs security checks on the original embedded URL before redirecting to it.
Cool, except it's a violation of privacy, it makes it impossible to quickly check whether the link goes to somewhere you trust, and it can make your email agent suspect that it's a scam.
Use `remove-safelinks` fairly early on to undo these in HTML and plain-text messages:

```
:0 fw
| remove-safelinks
```


## Removing 'external' warnings

Your institution might modify a message to alert you to the fact that it has not come from within that institution.
It might non-intrusively add a header field such as `X-External-Mail: yes`, which can be useful functionally, but it could also inject the likes of `[External]` into the subject, or bung a whole warning into the body of the message, e.g., `This email did not originate within your institution.`
This is very intrusive, and ends up polluting conversations between institutions.
Use a combination of rules to deal with this:

```
:0
* ^X-External-Mail: yes
{
  :0 h
  EXTERNAL_MAIL=| formail -cXX-External-Mail

  :0 fw
  | remove-external-sender -f $HOME/.config/posthack/ext1.yml

  :0 fhw
  | strip-label '[External Sender]' '[External]'
}
```

This block only applies to messages marked unambiguously with the special header field.
It then copies that field to an environment variable;
later commands will have access to it outside this block.
Then `remove-external-sender` demangles the message body by looking for text indicated by the YAML file.
Finally, various subject tags are stripped.

The configuration file `$HOME/.config/posthack/ext1.yml` can contain the likes of the following:

```
blocks:
  - 'This email did not originate within your institution.'
  - '<p>This email did not originate within your institution.</p>'
```

Each element of `blocks` is split into lines, and matched against exact lines in the message.


## IMAP delivery

If you keep your emails on a remote IMAP server, the provider might provide some filtering rules.
You might prefer `procmail`, but have no way to run it on the server.
You could fetch new mail off that server, and process it on a dedicated server at home, or on a VPS, but `procmail` won't be able to deliver back to specific folders on the server, as it can only natively deliver to local mbox or maildirs folders.
`push-imap` can be used in a `procmail` rule to deliver the message to a specific folder on an IMAP server.

*Caution!  Misconfiguration could result in lost emails!*

Create a file (say, `~/.config/posthack/config.yml`) to hold account details:

```
secrets: ~/.config/posthack/secrets.yml
default-account: default
accounts:
  - name: default
    hostname: imap.example.com
    username: fred
```

Also create a secure file `~/.config/posthack/secrets.yml` to hold passwords indexed by the value of the `name` field:

```
default: yeahright
```

Make sure the file is readable only by you:

```
chmod 600 ~/.config/posthack/secrets.yml
```

`push-imap` reads from `~/.config/posthack/config.yml` by default, but this is overridden by setting the environment variable `PUSHIMAP_CONFIG`, which is in turn overridden by the switch `-f somefile.yml`.
It then selects the account whose name is `default` by default, similarly overridden in turn by the field `default-account`, the environment variable `PUSHIMAP_ACCOUNT`, and the switch `-a otheraccount`.
Set `PUSHIMAP_ACCOUNT` and/or `PUSHIMAP_CONFIG` at the start of `.procmailrc`, if you don't want to use the defaults:

```
PUSHIMAP_CONFIG = $HOME/.pushimap.yml
PUSHIMAP_ACCOUNT = bt
```

Some servers use dots as separators for nested folders, and some use slashes.
You can first use `push-imap -l` to list folders in the account, showing what is used in each case.
It will also show how certain other special characters are escaped.

Now you can add terminating `procmail` rules that use `push-imap` to deliver to specific folders, using the strings that `push-imap -l` specifies.
For example, this one delivers Twitter notifications to `Alerts/News`:

```
:0 W
* ^From:.*info@(e\.)?twitter\.com
| push-imap -s -d "Alerts/News"
```

`-d` specifies the folder, escaped as shown by `push-imap -l`.
`-s` marks the message as 'seen' or 'read'.
You can also use `-F` to mark the message as flagged or starred.

The `W` flag on the `procmail` rule ensures that the message continues to be processed if the command fails.
You should have a catch-all at the end to drop messages by default in your inbox, and set `DEFAULT` so that the email is preserved locally:

```
## At the start

## Append to an mbox file.
DEFAULT = /var/mail/fred

## Or drop in a maildirs directory structure.
DEFAULT = /var/mail/fred.dirs/

# .
# .
# .

## At the end
:0 W
| push-imap -d "INBOX"
```

### Tagging external messages

A `push-imap` account configuration can contain a `tags` entry:

```
accounts:
  - name: default
    hostname: imap.example.com
    username: fred
    tags:
      - env: EXTERNAL_MAIL
        name: External
```

With this configuration, if the environment variable `EXTERNAL_MAIL` is non-empty, the tag `External` will be added to the message as it is delivered.
(Recall that `EXTERNAL_MAIL` is set by one of the `.procmailrc` configuration examples earlier.)
Your email user agent should be able to highlight such messages.

## IMAP purging

Your user agent might provide retention policies to clear out old messages from certain folders.
For example, it could retain only messages less than 90 days old in `Alerts/News`, or only the most recent 100 messages in `Alerts/Autobuilder`.

That's great, but it depends on having the user agent running, and if you use more than one (e.g., one at home, one at work), you either have to maintain two sets of policies, or keep one running at the place you're not.

`purge-imap` can be used to apply retention policies to a remote IMAP server.

*Caution!  Misconfiguration could result in losing the wrong emails!*

Add a `purge` entry to your account in `~/.config/posthack/config.yml`:

```
accounts:
  - name: default
    hostname: imap.example.com
    username: fred
    purge:
      - folder: Alerts/News
        max-age: 90
      - folder: Alerts/Notifications
        max-age: 500
      - folder: Alerts/Promotions
        max-age: 68
      - folder: Alerts/Autobuilder
        message-limit: 100
```

Use `push-imap -l` as before to get the escaped names of the folders in question.
Quote them correctly for YAML, if necessary.

When ready, set up an infrequent cronjob to purge the old messages:

```
PUSHIMAP_CONFIG=/home/fred/.config/posthack/config.yml

45 4 * * 3 purge-imap > "$HOME/.local/var/log/purge-bt.log" 2>&1
```


# Hints and tips

The following advice is for use of other tools in conjunction with those in this project.

## Directing emails to `procmail`

If you want to apply `procmail` filtering on your own server to emails on an external IMAP server, you have to get them delivered to your server somehow first.
One option is to get your email forwarded unconditionally to your own server over SMTP.
Another is to fetch it via POP or IMAP.

### Forwarding via SMTP

Your server will need to keep port 25 open to receive emails.
I've used `postfix` for this, but you must configure it correctly to prevent it being used as an open relay.
Only accept emails in envelopes addressing your specific server, and drop everything else.

A home server is problematic, as it will probably require port forwarding, and dynamic DNS.
If your external IP address changes, some messages might go through to someone else's network until DNS is updated!
If they're not listening on port 25, the message will probably be queued until the update is complete, but you're listening on 25, so why shouldn't they?

If you have a box at a fixed address you can SSH into, and which doesn't already have port 25 open, you could SSH-tunnel to it, so that all connections on that box transparently reach your home box.
You're calling out, so dynamic DNS is not relevant.
Use `autossh` to help keep the connection open.
If it's closed temporarily, the caller will likely queue the message until the connection is back up.
However, if you have that box, and the necessary permissions, why not just run `procmail` there?


### Polling

You can use `fetchmail` with `crontab` to pull messages periodically, but that might mean you don't get emails straight away.
You could poll more frequently, depending on what your email provider tolerates.
If you're polling, you can use POP or IMAP.

Alternatively, `fetchmail` can remain permanently connected to an IMAP server using the `idle` directive.
It will fetch email as soon as it arrives.
However, I have noticed that it can become insensitive under unknown conditions.
(Perhaps a problem with the server?)
This seems to be remedied with an occasional `SIGHUP`:

```
## At 01:20, 07:20, 13:20, 19:20, wake an idle fetchmail up.
20 1,7,13,19 * * * if [ -r "$HOME/.fetchmail.pid" ] ; then /bin/kill -HUP "$(/bin/cat "$HOME/.fetchmail.pid")" ; fi
```

This only works with IMAP, and only one account can be watched.

If you fetch from the remote server, and have `procmail` depositing emails back into it, avoid creating a loop whereby your emails are dropped back in `INBOX` by default, and `fetchmail` pulls from there!
Instead, use the remote server's native filtering facility to move all emails arriving by SMTP into (say) `INBOX/Incoming`, and have `fetchmail` pull only from there.
Make sure no `procmail` rule drops into `INBOX/Incoming`, and you've avoided the loop.


## Spam filters

I use an early `procmail` rule to restore a subject changed by some spam-detecting software:

```
:0 fhw
* ^X-Spam-Prev-Subject:
| formail -R X-Spam-Prev-Subject Subject -U Subject
```

The same software also provides lots of other `X-` fields to detect on, so there's no functional loss of information here.
A later rule uses these to drop the message in the spam folder.
If it turns out to be a mistake, it won't have a mangled subject when I manually move it back out.


## Logging

`procmail` and `fetchmail` both log.
Use `logrotate` to manage these logs, preventing them from growing indefinitely.
A cronjob could look like this:

```
## At 00:05 every night, rotate the logs.
5 0 * * * logrotate -s "$HOME/.local/var/lib/logrotate" "$HOME/.local/etc/logrotate.conf"
```

The configuration in `~/.local/etc/logrotate.conf` could be:

```
/home/fred/.local/var/log/fetchmail.log {
  rotate 5
  missingok
  size 100k
  postrotate
    if [ -r "$HOME/.fetchmail.pid" ] ; then \
      /bin/kill -HUP "$(/bin/cat "$HOME/.fetchmail.pid")" ; \
    fi
  endscript
  create 640 fred fred
  compress
  delaycompress
  nomail
}

/home/fred/.local/var/log/procmail.log {
  rotate 5
  missingok
  size 100k
  compress
  delaycompress
  nomail
}
```
