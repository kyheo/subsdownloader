import os
import optparse

import logging

def parse_options():
    parser = optparse.OptionParser()
    parser.add_option('--log-level', type='string', dest='log_level', default='DEBUG', help='Define log level (DEBUG, INFO, etc).')
    parser.add_option('--config', type='string', dest='config', default=None, help='Load config from file.')
    parser.add_option('--lang', type='string', dest='lang', default='spa', help='Subtitle download language.')

    dir_group = optparse.OptionGroup(parser, 'Directory options')
    dir_group.add_option('-r', '--recursive', dest='recursive', action='store_true', default=False, help='Recursively look for files.')
    dir_group.add_option('--exclude', type='string', dest='exclude', action='append', default=[], help='Exclude files regular expressions. (Multiple)')
    dir_group.add_option('--exclude-subs', type='string', dest='exclude_subs', help='Exclude subs in this directory.')
    dir_group.add_option('--source', type='string', dest='source', default='q-in', help='Source directory.')
    dir_group.add_option('--dest', type='string', dest='dest', help='Destination directory. Default --source.')
    dir_group.add_option('--regex', type='string', dest='regex', action='append', default=[], help='Glob sources regex. This overrides --source. (Multiple)')
    parser.add_option_group(dir_group)

    quota_group = optparse.OptionGroup(parser, 'Quota options')
    quota_group.add_option('--quota-file', type='string', dest='quota_file', default='/tmp/quota-file.json', help='Track file for quota limits. Should persist over time.')
    quota_group.add_option('--quota-limit', type='int', dest='quota_limit', default=200, help='Max number of allowed downloads. Change this at your own risk.')
    parser.add_option_group(quota_group)

    email_group = optparse.OptionGroup(parser, 'Email options')
    email_group.add_option('--notify', dest='notify', action='store_true', default=False, help='Notification email on download.')
    email_group.add_option('--from', type='string', dest='from_', help='Your email.')
    email_group.add_option('--to', type='string', dest='to', action='append', help='Destination email. (Multiple)')
    email_group.add_option('--smtp-server', type='string', dest='smtp_server', default='smtp.gmail.com', help='SMTP server.')
    email_group.add_option('--smtp-port', type='string', dest='smtp_port', default=587, help='SMTP Server port.')
    email_group.add_option('--smtp-user', type='string', dest='smtp_user', help='Server user.')
    email_group.add_option('--smtp-pass', type='string', dest='smtp_pass', help='Server password.')
    email_group.add_option('--use-tls', dest='smtp_tls', action='store_true', default=True, help='Use tls.')
    parser.add_option_group(email_group)

    (options, args) = parser.parse_args()

    if options.config:
        try:
            fname = os.path.basename(options.config)
            module, ext = os.path.splitext(fname)
            C = __import__(module)
            parser.set_defaults(**C.options)
            (options, args) = parser.parse_args()
        except Exception, e:
            print '- Error:', e
            import sys
            sys.exit(1)

    options.log_level = getattr(logging, options.log_level)

    # Hardcoded values, shouldn't change at all
    options.api_url = 'http://api.opensubtitles.org/xml-rpc'
    options.api_user_agent = 'Kyheo SubsDown v0.1'

    if not options.dest:
        options.dest = options.source
    
    logging.basicConfig(
        level   = options.log_level,
        format  = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s',
        datefmt = '%Y-%m-%d %H:%M:%S',
        )

    return options



