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
import logging

# Set full path to in and out queues
config = {'opensubtitles': {'url': 'http://api.opensubtitles.org/xml-rpc',
                            'user-agent': 'Kyheo SubsDown v0.1',
                            'language': 'spa'},
          'queues': {'in': 'q-in',
                     'out': 'q-out',},
          'quota': {'file': '/tmp/quota-file.json',
                    'limit': 200,},
          'log-level': logging.DEBUG,
          }

logging.basicConfig(level = config['log-level'],
                    format  = '%(asctime)s - %(levelname)-s - %(name)s - %(message)s', 
                    datefmt = '%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)


class Quota(object):

    def __init__(self, config):
        super(Quota, self).__init__()
        self.config = config

        self.date = None
        self.qty = 0

        self.initialize()


    def initialize(self):
        try:
            log.debug('Loading quota information')
            fp = open(self.config['file'], 'r')
            data = json.load(fp)
            fp.close()
            self.qty = data['qty']
            self.date = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
            self.date = self.date.date()
        except IOError:
            log.debug('  No quota file, creating one')
            self.save()


    def reached(self):
        today = datetime.date.today()
        if self.date == today and self.qty >= self.config['limit']:
            return True
        return False

    
    def save(self):
        data = {'date': datetime.date.today().isoformat(),
                'qty': self.qty}
        fp = open(self.config['file'], 'w')
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




def main(config):
    files = os.listdir(config['queues']['in'])
    if not files:
        log.debug('No files, ending')
        return

    quota = Quota(config['quota'])

    if quota.reached():
        log.debug('Quota reached')
        return

    server = xmlrpclib.Server(config['opensubtitles']['url']);
    login = server.LogIn('', '', '', config['opensubtitles']['user-agent'])
    if login['status'] == '200 OK':
        token = login['token']
        log.debug('Logged in with token %s' % (token,))
    else:
        log.error('Couldn\'t log in.')
        return

    #Search 
    for file in files:
        try:
            fname = os.path.join(config['queues']['in'], file)
            log.debug('Processing ' + fname)
            hash, size = hashFile(fname)
            log.debug('Searching for ' + file)
            lang = config['opensubtitles']['language']
            data = server.SearchSubtitles(token, [{'sublanguageid': lang, 
                                                   'moviehash': str(hash), 
                                                   'moviebytesize': size}])
        except Exception,e:
            log.error(str(e))
            # Lets try with the next file if any.
            continue

        if data['data']:
            for d in data['data']:
                try:
                    # TODO: Catch exceptions individually
                    filename, fileext = os.path.splitext(file)
                    sub_fname = '%s.%s' % (filename, d['SubFormat'])

                    log.info('Downloading %s' % (sub_fname,))

                    sub_data = server.DownloadSubtitles(token,
                                                        [d['IDSubtitleFile']])
                    sub_content = base64.b64decode(sub_data['data'][0]['data']) 
                    sf_data = cStringIO.StringIO(sub_content)
                    body = gzip.GzipFile('', 'r', 0, sf_data).read()

                    # Write subtitle file
                    dst_sub_name = os.path.join(config['queues']['out'], sub_fname)
                    fp = open(dst_sub_name, 'wb')
                    fp.write(body)
                    fp.close()
                    dst_file = os.path.join(config['queues']['out'], file)
                    shutil.move(fname, dst_file)
                    quota.qty += 1
                    # Break for, don't want to loop over the next subs
                    break
                except Exception, e:
                    log.error(str(e))
        else:
            log.debug(' Nothing found')

    #LogOut
    logout = server.LogOut(token)
    if logout['status'] == '200 OK':
        log.debug('Logged out')

    quota.save()


if __name__ == '__main__':
    log.info('Starting')
    main(config)
    log.info('Ending')
