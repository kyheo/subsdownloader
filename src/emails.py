import smtplib
from email.mime.text import MIMEText


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

