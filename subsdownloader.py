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

# Set user and pass values.
config = {'url': 'http://api.opensubtitles.org/xml-rpc',
          'user': '', # opensubtitles user
          'pass': '', # opensubtitles pass
          'user-agent': 'Kyheo SubsDown v0.1',
          'in-dir': 'q-in', # Full path to in dir 
          'out-dir': 'q-out', # Full path to out dir
          'log-level': logging.DEBUG,
          'quota': {'file': '/tmp/quota-file.json',
                    'limit': 200,},
          }


logging.basicConfig(level = config['log-level'],
                    format  = '%(asctime)s - %(levelname)-s - %(name)s - %(message)s', 
                    datefmt = '%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)


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


def quota_save_file(config, qty=0):
    quota_data = {'date': datetime.date.today().isoformat(), 
                  'qty': 0}
    fp = open(config['file'], 'w')
    json.dump(quota_data, fp)
    fp.close()


def quota_reached(config):
    try:
        fp = open(config['file'], 'r')
        data = json.load(fp)
        fp.close()
        data['date'] = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
        data['date'] = data['date'].date()
        if (data['date'] < datetime.date.today()) or \
           (data['date'] == datetime.date.today() and \
            data['qty'] < config['limit']):
            return False
        else:
            return True
    except IOError:
        log.debug('No quota file, creating an empty one')
        quota_save_file(config)
    return False


def main(config):
    files = os.listdir(config['in-dir'])
    if not files:
        log.debug('No files, ending')
        return

    if quota_reached(config['quota']):
        log.debug('Quota reached')
        return

    server = xmlrpclib.Server(config['url']);
    login = server.LogIn(config['user'], config['pass'], '',
                         config['user-agent'])
    if login['status'] == '200 OK':
        token = login['token']
        log.debug('Logged in with token %s' % (token,))
    else:
        log.error('Couldn\'t log in.')
        return

    #Search 
    subs_downloaded = 0
    for file in files:
        try:
            fname = os.path.join(config['in-dir'], file)
            log.debug('Processing ' + fname)
            hash, size = hashFile(fname)
            log.debug('Searching for ' + file)
            data = server.SearchSubtitles(token, [{'sublanguageid': 'spa', 
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
                    dst_sub_name = os.path.join(config['out-dir'], sub_fname)
                    fp = open(dst_sub_name, 'wb')
                    fp.write(body)
                    fp.close()
                    dst_file = os.path.join(config['out-dir'], file)
                    shutil.move(fname, dst_file)
                    subs_downloaded += 1
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

    quota_save_file(config['quota'], subs_downloaded)


if __name__ == '__main__':
    log.info('Starting')
    main(config)
    log.info('Ending')
