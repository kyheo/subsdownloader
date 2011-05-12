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
import hashlib

import optparse

import glob

import logging


def parse_options():
    parser = optparse.OptionParser()
    parser.add_option('--log-level', type='string', dest='log_level', default='DEBUG', help='Define log level (DEBUG, INFO, etc).')
    parser.add_option('--config-module', type='string', dest='config_module', default=None, help='Load config from module (no py extension).')
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

    # Hardcoded values, shouldn't change at all
    options.api_url = 'http://api.opensubtitles.org/xml-rpc'
    options.api_user_agent = 'Kyheo SubsDown v0.1'

    if not options.dest:
        options.dest = options.source
    
    logging.basicConfig(level = options.log_level,
                        format = '%(asctime)s - %(levelname)-8s - %(message)s', 
                        datefmt = '%Y-%m-%d %H:%M:%S')

    return options


def get_filenames(options):
    logging.debug('Getting files')

    exclude_regex = []
    for pattern in options.exclude:
        exclude_regex.append(re.compile(pattern))

    file_list = []
    if options.regex:
        for regex in options.regex:
            file_list += [ file for file in glob.glob(regex) if os.path.isfile(file) ]
    else:
        for root, dirs, files in os.walk(options.source):
            for file in files:
                match = False
                fname = os.path.join(root, file)
                for reg_exp in exclude_regex:
                    if reg_exp.search(fname):
                        match = True
                        break
                if not match:
                    file_list.append(fname)

            if not options.recursive:
                break

    logging.info('%d files found' % (len(file_list)))
    return file_list


def get_excluded_subs(options):
    logging.debug('Looking for excluded subs')
    excluded_subs = []
    if options.exclude_subs:
        for file in os.listdir(options.exclude_subs):
            fp = open(os.path.join(options.exclude_subs, file), 'r')
            h = hashlib.md5()
            h.update(fp.read())
            fp.close()
            excluded_subs.append(h.hexdigest())
    logging.info('%d excluded subs.' % (len(excluded_subs),))
    return excluded_subs


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
    email['From'] = options.from_
    email['To'] = ', '.join(options.to)

    server = smtplib.SMTP(options.smtp_server, options.smtp_port)
    if options.smtp_tls:
        server.starttls()
    server.login(options.smtp_user, options.smtp_pass)
    server.sendmail(options.from_, options.to, email.as_string())
    server.quit()


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


def main(options):
    files = get_filenames(options) 
    if not files:
        logging.info('No files, ending')
        return

    quota = Quota(options)
    
    if quota.reached():
        logging.info('Quota reached, ending')
        return

    excluded_subs = get_excluded_subs(options)

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
            data = server.SearchSubtitles(token, [{'sublanguageid': options.lang, 
                                                   'moviehash': str(hash), 
                                                   'moviebytesize': str(size)}])
        except Exception,e:
            logging.error(str(e))
            # Lets try with the next file if any.
            continue

        if data['data']:
            for d in data['data']:
                if d['SubHash'] in excluded_subs:
                    logging.debug('Buggy sub, next !')
                    continue
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
                    if options.dest:
                        out_dirs = options.dest
                    else:
                        out_dirs = dirs
 
                    if not os.path.exists(out_dirs):
                        logging.debug('Creating out directory')
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
            logging.debug('Nothing found')

    #LogOut
    logout = server.LogOut(token)
    if logout['status'] == '200 OK':
        logging.debug('Logged out')

    #Send notification email
    if options.notify == True:
        logging.debug('Sending notification email')
        send_notification_email(options, downloaded)

    quota.save()


if __name__ == '__main__':
    options = parse_options()
    logging.info('Starting')
    main(options)
    logging.info('Ending')
