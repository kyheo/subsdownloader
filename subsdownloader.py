#! /usr/bin/env python
import os
import struct
import shutil
import base64
import xmlrpclib
import cStringIO
import gzip
import json
import datetime
import smtplib
from email.mime.text import MIMEText
import re

import optparse

import logging


def parse_options():
    parser = optparse.OptionParser()
    parser.add_option('--log-level', type=str, dest='log_level', default='DEBUG', help='Define log level (DEBUG, INFO, etc)'       )
    parser.add_option('--config-module', type=str, dest='config_module', default=None, help='Load config from module (no py extension).')

    dir_group = optparse.OptionGroup(parser, 'Directory options')
    dir_group.add_option('-r', '--recursive', dest='dir_recursive', action='store_true', default=False, help='Recursive look for files.')
    dir_group.add_option('--exclude', type=str, dest='dir_exclude', action='append', default=[], help='Exclude regular expressions')

    dir_group.add_option('--dir-in', dest='dir_in', default='q-in', help='Source directory')
    dir_group.add_option('--dir-out', dest='dir_out', help='Destination directory')
    parser.add_option_group(dir_group)

    quota_group = optparse.OptionGroup(parser, 'Quota options')
    quota_group.add_option('--quota-file' , type=str, dest='quota_file' , default='/tmp/quota-file.json', help='Track file for quota limits. Should persist over time')
    quota_group.add_option('--quota-limit', type=int, dest='quota_limit', default=200                   , help='Max number of allowed downloads.')
    parser.add_option_group(quota_group)

    email_group = optparse.OptionGroup(parser, 'Email options')
    email_group.add_option('--email-notify', dest='email_notify', action='store_true', default=False, help='Send notification email')
    email_group.add_option('--email-from', dest='email_from', help='Your email')
    email_group.add_option('--email-to', dest='email_to', action='append', help='Destination email. One per destination address.')
    email_group.add_option('--email-smtp-server', dest='email_smtp', default='smtp.gmail.com', help='Relay server')
    email_group.add_option('--email-smtp-port', dest='email_port', default=587, help='Server port')
    email_group.add_option('--email-use-tls', dest='email_tls', action='store_true', default=True,  help='Use tls')
    email_group.add_option('--email-user', dest='email_user', help='Server user')
    email_group.add_option('--email-password', dest='email_password', help='Server password')
    parser.add_option_group(email_group)

    api_group = optparse.OptionGroup(parser, 'Open Subtitle options')
    api_group.add_option('--api-url', dest='api_url', default='http://api.opensubtitles.org/xml-rpc', help='API url')
    api_group.add_option('--api-user-agent', dest='api_user_agent', help='App User Agent', default='Kyheo SubsDown v0.1')
    api_group.add_option('--api-language', dest='api_language', help='Subtitle download language', default='spa')
    parser.add_option_group(api_group)

    (options, args) = parser.parse_args()

    if options.config_module:
        try:
            C = __import__(options.config_module)
            parser.set_defaults(**C.options)
            (options, args) = parser.parse_args()
        except Exception, e:
            print '- Error:', e
            import sys
            sys.exit(1)

    options.log_level = getattr(logging, options.log_level)

    if not options.dir_out:
        options.dir_out = options.dir_in
    
    logging.basicConfig(level = options.log_level,
                        format = '%(asctime)s - %(levelname)-8s - %(message)s', 
                        datefmt = '%Y-%m-%d %H:%M:%S')

    return options




def get_filenames(options, directory=None):
    if directory is None:
        directory = options.dir_in
    logging.debug('Getting files')

    reg_exps = []
    for pattern in options.dir_exclude:
        reg_exps.append(re.compile(pattern))

    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            match = False
            fname = os.path.join(root, file)
            for reg_exp in reg_exps:
                if reg_exp.search(fname):
                    match = True
                    break
            if not match:
                file_list.append(fname)

        if not options.dir_recursive:
            break

    logging.info('%d files found' % (len(file_list)))
    return file_list



class Quota(object):

    def __init__(self, options):
        super(Quota, self).__init__()
        self.options = options

        self.date = None
        self.qty = 0

        self.initialize()


    def initialize(self):
        try:
            logging.debug('Loading quota information')
            fp = open(self.options.quota_file, 'r')
            data = json.load(fp)
            fp.close()
            self.qty = data['qty']
            self.date = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
            self.date = self.date.date()
        except IOError:
            logging.debug('  No quota file, creating one')
            self.save()


    def reached(self):
        today = datetime.date.today()
        if self.date == today and self.qty >= self.options.quota_limit:
            return True
        return False

    
    def save(self):
        data = {'date': datetime.date.today().isoformat(),
                'qty': self.qty}
        fp = open(self.options.quota_file, 'w')
        json.dump(data, fp)
        fp.close()




def hashFile(name):
    """Opensubtitles hash function modified to return not only the hash but
    also the file size.
    http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes#Python
    """
    longlongformat = 'q'  # long long 
    bytesize = struct.calcsize(longlongformat) 
        
    f = open(name, "rb") 
        
    filesize = os.path.getsize(name) 
    hash = filesize 
        
    if filesize < 65536 * 2: 
        raise Exception("SizeError")
     
    for x in range(65536/bytesize): 
        buffer = f.read(bytesize) 
        (l_value,)= struct.unpack(longlongformat, buffer)  
        hash += l_value 
        hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number  

    f.seek(max(0,filesize-65536),0) 
    for x in range(65536/bytesize): 
        buffer = f.read(bytesize) 
        (l_value,)= struct.unpack(longlongformat, buffer)  
        hash += l_value 
        hash = hash & 0xFFFFFFFFFFFFFFFF 
     
    f.close() 
    returnedhash =  "%016x" % hash 
    return returnedhash, filesize 




def send_notification_email(options, subs):
    msg = 'The following subtitles were downloaded:\n\n'
    msg+= '\n'.join(['- %s' % (s, ) for s in subs])
    msg+= '\n\nRegards, Subsdownloader'
    email = MIMEText(msg)
    email['Subject'] = 'Subtitle Download Notification'
    email['From'] = options.email_from
    email['To'] = ', '.join(options.email_to)

    server = smtplib.SMTP(options.email_smtp, options.email_port)
    if options.email_tls:
        server.starttls()
    server.login(options.email_user, options.email_password)
    server.sendmail(options.email_from, options.email_to, email.as_string())
    server.quit()




def main(options):
    files = get_filenames(options) 
    if not files:
        logging.info('No files, ending')
        return

    quota = Quota(options)
    
    if quota.reached():
        logging.info('Quota reached, ending')
        return

    server = xmlrpclib.Server(options.api_url);
    login = server.LogIn('', '', '', options.api_user_agent)
    if login['status'] == '200 OK':
        token = login['token']
        logging.debug('Logged in with token %s' % (token,))
    else:
        logging.error('Couldn\'t log in.')
        return

    #Search
    downloaded = []
    for file in files:
        try:
            logging.info('Processing ' + file)
            hash, size = hashFile(file)
            data = server.SearchSubtitles(token, [{'sublanguageid': options.api_language, 
                                                   'moviehash': str(hash), 
                                                   'moviebytesize': str(size)}])
        except Exception,e:
            logging.error(str(e))
            # Lets try with the next file if any.
            continue

        if data['data']:
            for d in data['data']:
                try:
                    if quota.reached():
                        logging.info('Quota reached, ending')
                        break
                    # TODO: Catch exceptions individually
                    dirs, fname = os.path.split(file)
                    filename, fileext = os.path.splitext(fname)
                    
                    sub_fname = '%s.%s' % (filename, d['SubFormat'])

                    # Download subtitle
                    logging.info('Downloading %s' % (sub_fname,))
                    sub_data = server.DownloadSubtitles(token,
                                                        [d['IDSubtitleFile']])
                    sub_content = base64.b64decode(sub_data['data'][0]['data']) 
                    sf_data = cStringIO.StringIO(sub_content)
                    body = gzip.GzipFile('', 'r', 0, sf_data).read()

                    # Create output dir
                    out_dirs = dirs.replace(options.dir_in, options.dir_out, 1)
                    if options.dir_in != options.dir_out:
                        logging.debug('Creating out directory')
                        if not os.path.exists(out_dirs):
                            os.makedirs(out_dirs)

                        # Move video file 
                        dst_file = os.path.join(out_dirs, fname)
                        shutil.move(file, dst_file)
                        quota.qty += 1
                        downloaded.append(sub_fname)

                    # Write subtitle file
                    dst_sub_name = os.path.join(out_dirs, sub_fname)
                    fp = open(dst_sub_name, 'wb')
                    fp.write(body)
                    fp.close()

                    # Break for, don't want to loop over the next subs
                    break
                except Exception, e:
                    logging.error(str(e))
        else:
            logging.debug(' Nothing found')

    #LogOut
    logout = server.LogOut(token)
    if logout['status'] == '200 OK':
        logging.debug('Logged out')

    #Send notification email
    if options.email_notify == True:
        logging.debug('Sending notification email')
        send_notification_email(options, downloaded)

    quota.save()


if __name__ == '__main__':
    options = parse_options()
    logging.info('Starting')
    main(options)
    logging.info('Ending')
