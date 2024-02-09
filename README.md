# Purpose

These Python scripts are intended for use mostly in `procmail` rules, and provide the following functionality:

- Match on `Subject`, even if encoded.

- Strip mailing-list `[tags]`.

- Unpack forwarded emails as attachments.

- Restore mangled 'safelinks'.

- Strip 'external' warnings.

- Deliver to IMAP folders, starred and/or marked as read, and with custom tags.

- Purge old messages from IMAP servers.


# Installation

Installation requires [Binodeps](https://github.com/simpsonst/binodeps).

To install to the default location `/usr/local`:

```
make
sudo make install
```

You might prefer to create a `config.mk` adjacent to `Makefile`, to install in another location:

```
## In config.mk
PREFIX=$(HOME)/.local
```

Commands intended for use in `.procmailrc` are installed in `bin/`, while commands for cronjobs are installed in `share/`.


## Dependencies

```
sudo apt-get install python3-bs4
```

# Common configuration

Several commands require configuration:

- `push-imap`

- `purge-imap`

- `list-imap`

- `remove-external-sender`

By default, they read YAML configuration from `~/.config/posthack/config.yml`.
This is overridden by the value of the environment variable `POSTHACK_CONFIG`, which in turn is overridden by the `-f` switch of these commands.


## IMAP accounts

*Caution!
Misconfiguration could result in lost emails!*

`push-imap` and `purge-imap` require access to one or more IMAP accounts.
The main configuration needs a field `accounts` containing account details:

```
secrets: ~/.config/posthack/secrets.yml
default-account: default
accounts:
  - name: default
    hostname: imap.example.com
    username: fred
```

Each entry requires a `name` field which identifies the account within Posthack commands.
The account that a given invocation of a command uses is set by the `-a` switch, by the `POSTHACK_ACCOUNT` environment variable, by the `default-account` field, or by the literal `default`, in that order of precedence.

Each entry also requires `hostname` and `username` fields.
A `port` field is optional, and defaults to 993.

Passwords are stored in the file specified by `secrets` (or `~/.config/posthack/secrets.yml` by default), indexed by the local account name.
For example:

```
default: yeahright
```

Make sure the file is readable only by you:

```
chmod 600 ~/.config/posthack/secrets.yml
```


## Dealing with encoded subjects

The subject of an email is held in a header field `Subject`, and so it's usually restricted to the `US-ASCII` charset.
Other charsets are possible by encoding them with the likes of `=?utf-8?q?caf=C3=A9?=`.
`procmail` presents such content as is, not decoded, making it difficult to detect certain patterns consistently if they happen to have been included in such an encoding.
Use `decode-header` to convert an encoded subject into UTF-8:

```
SUBJECT=`formail -cXSubject: | decode-header`
```

You can then use this condition to test against the decoded subject:

```
* SUBJECT ?? ^Subject:.*ACTION REQUIRED
```


## Stripping subject tags

Emails sent to lists often have tags prefixed to their subjects, e.g., `[EDAS-CFP]` or `[modfoo]`, so you know they are being delivered to you as a member of the list.
They might also be added by your institution to indicate some processing or status of the message, such as `[External]` or `[SPAM]`.
In many cases, these conditions are also indicated by header fields that are not normally displayed to the user, such as `X-Spam-Status: YES` or `List-Id: <modfoo.example.org>`, so the subject tags are functionally redundant in conjunction with `procmail` rules that use these hidden fields to direct messages to dedicated folders.
Use `strip-label` to remove matching strings from the subject, along with any trailing white space:

```
:0 fhw
* ^List-Id:.*<modfoo\.example\.org>
| strip-label '[modfoo]'
```

Multiple strings can be specified in a single command.


## Unpacking emails as attachments

Sometimes you find the email you're expecting as an attachment in another.
Perhaps a spam filter that you have no control over thinks you're the sender, and is 'returning' it to you, surrounded by an explanatory message.
Perhaps you've had to configure an email account to forward emails to you, but it mangles them by destroying the `Message-Id` field and replacing it with something less than useless, breaking all topic threading, so you tell it to forward each message as an attachment instead.
Either way, you want the embedded message extracted, and processed like other messages.
Look for header fields that identify these kinds of messages, and then pipe through `unpack-email`.
For example, extract a message thought to be spam, and add a header to record its prior form:

```
:0
* ^X-MS-Exchange-Message-Is-Ndr:
{
  :0 fw
  | unpack-email -t message/rfc822

  :0 fhw
  | formail -A 'X-Original-Form: non-delivery'
}
```

Or extract a message forwarded as an attachment:

```
:0
* ^From:.*\<the-dodgy-account@example\.com\>
* ^X-MS-Has-Attach: yes
* ^X-MS-Exchange-Inbox-Rules-Loop:.*\<the-dodgy-account@example\.com\>
{
  :0 fw
  | unpack-email

  :0 fhw
  | formail -A 'X-Original-Form: forward-as-attachment'
}
```

Arguments allow you to walk a multipart message hierarchy:

- `-s *num*` &ndash; Skip `num` parts of the current message.

- `-t *type*` &ndash; Skip parts not of content type `type`.

- `-d *disp*` &ndash; Skip parts not of content disposition `disp`.

- `-n *name*` &ndash; Skip parts without a content disposition name `name`.

- `--` &ndash; Select the first part matching the above criteria, and make it the current message.

`-s`, `-t`, `-d` and `-n` can be combined as a logical AND.
`-s 2 -t message/rfc822 -d attachment` selects the third part that is both an RFC822 message and an attachment.
These are reset with each `--`, so new criteria can be specified at each depth.

If no arguments are supplied, `-s 1` is assumed.


## Restoring 'safe' links

Sometimes, your email provider will add 'safe' links, i.e., it will scan the email for links, and replace the URL with another that embeds it but points to some specific site of its own.
If you follow the link, you first go to this site, which performs security checks on the original embedded URL before redirecting to it.
Cool, except it's a violation of privacy, it makes it impossible to quickly check whether the link goes to somewhere you trust, and it can make your email agent suspect that it's a scam.
Use `remove-safelinks` fairly early on to undo these in HTML and plain-text messages:

```
:0 fw
| remove-safelinks
```

Currently, it only handles links to the domain `safelinks.protection.outlook.com`.


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
  | remove-external-sender -a home

  :0 fhw
  | strip-label '[External Sender]' '[External]'
}
```

This block only applies to messages marked unambiguously with the special header field.
It then copies that field to an environment variable;
later commands will have access to it outside this block.
(The actual value isn't important, only that it's non-empty.)
Then `remove-external-sender` demangles the message body by looking for text indicated by configuration.
Finally, various subject tags are stripped.

The configuration file must contain a `blocks` entry, which itself can contain the likes of the following:

```
blocks:
  home:
    - ~/.config/posthack/blocks/form*.txt
```

By specifying `-a home` (or by having `default-account: home` in the configuration), files matching the listed names are read and matched against lines in the input message body.
Lines from the message are decoded according to `Content-Transfer-Encoding` and the charset of `Content-Type` before matching lines in the listed files.
Remaining lines are re-encoded and concatenated to form the resulting message.
In a multipart message, each part is processed separately.


## IMAP delivery

If you keep your emails on a remote IMAP server, the provider might provide some limited filtering rules.
You might prefer `procmail`, but have no way to run it on the server.
You could fetch new mail off that server, and process it on a dedicated server at home, or on a VPS, but `procmail` won't be able to deliver back to specific folders on the server, as it can only natively deliver to local mbox or maildirs folders.
`push-imap` can be used in a `procmail` rule to deliver the message to a specific folder on an IMAP server.

`push-imap` recognizes the switches `-f` and `-a`, and the environment variables `POSTHACK_CONFIG` and `POSTHACK_ACCOUNT`, to select the configuration file and IMAP account.

Some servers use dots as separators for nested folders, and some use slashes.
You can first use `list-imap` to list folders in the account, showing what is used in each case.
It will also show how certain other special characters are escaped.

Now you can add terminating `procmail` rules that use `push-imap` to deliver to specific folders, using the strings that `list-imap` specifies.
For example, this one delivers Twitter notifications to `Alerts/News`:

```
:0 W
* ^From:.*info@(e\.)?twitter\.com
| push-imap -s -d "Alerts/News"
```

`-d` specifies the folder, escaped as shown by `list-imap`.
`-s` marks the message as 'seen' or 'read'.
You can also use `-F` to mark the message as flagged or starred.

The `W` flag on the `procmail` rule ensures that the message continues to be processed if the command fails.


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

With this configuration, if the environment variable `EXTERNAL_MAIL` is non-empty, `push-imap` will add the tag `External` to the message as it is delivered.
(Recall how `EXTERNAL_MAIL` is set by one of the `.procmailrc` configuration examples earlier.)
Your email user agent should be able to highlight such messages.

# Background processing

## IMAP purging

Your user agent might provide retention policies to clear out old messages from certain folders.
For example, it could retain only messages less than 90 days old in `Alerts/News`, or only the most recent 100 messages in `Alerts/Autobuilder`.
That's great, but it depends on having the user agent running, and if you use more than one (e.g., one at home, one at work), you either have to maintain two sets of policies, or keep one running at the place you're not.

`purge-imap` can be used headless to apply retention policies to a remote IMAP server.

*Caution!
Misconfiguration could result in losing the wrong emails!*

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

Use `list-imap` as before to get the escaped names of the folders in question.
Quote them correctly for YAML, if necessary.

When ready, set up an infrequent cronjob to purge the old messages:

```
POSTHACK_CONFIG=/home/fred/.config/posthack/config.yml

45 4 * * 3 /usr/local/share/posthack/purge-imap > "$HOME/.local/var/log/purge-default.log" 2>&1
```

Purged messages will end up in the folder tagged `\Trash`.


# Hints and tips

The following advice is for use of other tools in conjunction with those presented here.


## General `procmail` caution

It's easy to make mistakes in a `.procmailrc` file, so be cautious, and test things out.
Start by collecting sample emails demonstrating various characteristics you want to filter on, as well as those that complicate processing (`multipart/alternative` messages, non-ASCII subject lines, base64-encoded bodies, etc).
Store each email in a separate file (e.g., `samp-msg-1.eml`).
Work on an undeployed configuration, e.g., `procmailrc.test`, and only copy it into place when tested.
Test with a single message like this:

```
procmail -m VERBOSE=yes ~/procmailrc.test < sam-msg-1.eml
```

Ensure that you still get a message somehow, even if processing failed.
Set `DEFAULT` to store the message locally as a last resort.
Your first rule could also keep an unaltered copy of all messages on the server.
The last rule should drop everything into your inbox.
For example:

```
## At the start

## Append to a local mbox file.
DEFAULT = /var/mail/fred

## Or drop into a local maildirs directory structure.
DEFAULT = /var/mail/fred.dirs/

## Keep a copy of all original messages for debugging.
:0 c
| push-imap -s -d "Originals"

## Your actual rules would go here.
# .
# .
# .

## Drop everything in the inbox.
:0 W
| push-imap -d "INBOX"
```



## Directing emails to `procmail`

If you want to apply `procmail` filtering on your own server to emails on an external IMAP server, you have to get them delivered to your server somehow first.
One option is to get your email forwarded unconditionally to your own server over SMTP.
Another is to fetch it via POP or IMAP.

### Forwarding via SMTP

Your server will need to keep port 25 open to receive emails;
I've used `postfix` for this.
Whatever you use, make sure you configure it correctly to prevent it being used as an open relay.
Only accept emails in envelopes addressing your specific server, and drop everything else.

A home server is problematic, as it will probably require port forwarding, and dynamic DNS.
If your external IP address changes, some messages might go through to someone else's network until DNS is updated!
If they're not listening on port 25, the message will probably be queued until the update is complete, but you're listening on 25, so why shouldn't they?

If you have a box at a fixed address you can SSH into, and which doesn't already have port 25 open, you could SSH-tunnel to it, so that all connections on that box transparently reach your home box.
You're calling out, so port forwarding and dynamic DNS are not relevant.
Use `autossh` to help keep the connection open.
If it's closed temporarily, the caller will likely queue the message until the connection is back up.
However, if you have that box, and the necessary permissions, why not just run `procmail` there?


### Polling

You can use `fetchmail` with `crontab` to pull messages periodically, but that might mean you don't get emails straight away.
You could poll more frequently, depending on what your email provider tolerates.
If you're polling, you can use POP or IMAP.

Alternatively, `fetchmail` can remain permanently connected to an IMAP server using the `idle` directive.
It will fetch email as soon as it arrives.
This only works with IMAP, and only one account can be watched.
However, I have noticed that it can become insensitive under unknown conditions.
(Perhaps a problem with the server?)
This seems to be remedied with an occasional `SIGHUP`:

```
## At 01:20, 07:20, 13:20, 19:20, wake an idle fetchmail up.
20 1,7,13,19 * * * if [ -r "$HOME/.fetchmail.pid" ] ; then /bin/kill -HUP "$(/bin/cat "$HOME/.fetchmail.pid")" ; fi
```

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
