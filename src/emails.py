import smtplib
from email.mime.text import MIMEText

    #@TODO: Improve this
    #email_group = optparse.OptionGroup(parser, 'Email options')
    #email_group.add_option('--notify', dest='notify', action='store_true', default=False, help='Notification email on download.')
    #email_group.add_option('--from', type='string', dest='from_', help='Your email.')
    #email_group.add_option('--to', type='string', dest='to', action='append', default=[], help='Destination email. (Multiple)')
    #email_group.add_option('--smtp-server', type='string', dest='smtp_server', default='smtp.gmail.com:587', help='SMTP server:SMTP port. Default: smtp.gmail.com:587.')
    #email_group.add_option('--smtp-creds', type='string', dest='smtp_user', help='Server user:password.')
    #email_group.add_option('--use-tls', dest='smtp_tls', action='store_true', default=True, help='Use tls.')
    #parser.add_option_group(email_group)
    #options.to = remove_dups(options.to) 


def send_notification_email(options, subs):
    msg = 'The following subtitles were downloaded:\n\n'
    msg+= '\n'.join(['- %s' % (s, ) for s in subs])
    msg+= '\n\nRegards, Subsdownloader'
    email = MIMEText(msg)
    email['Subject'] = 'Subtitle Download Notification'
    email['From'] = options.from_
    email['To'] = ', '.join(options.to)

    server = smtplib.SMTP(options.smtp_server, options.smtp_port)
    if options.smtp_tls:
        server.starttls()
    server.login(options.smtp_user, options.smtp_pass)
    server.sendmail(options.from_, options.to, email.as_string())
    server.quit()

