#! /usr/bin/env python
import os
import struct
import shutil
import base64
import xmlrpclib
import cStringIO
import gzip
import logging

# Set user and pass values.
config = {'url': 'http://api.opensubtitles.org/xml-rpc',
          'user': '', # opensubtitles user
          'pass': '', # opensubtitles pass
          'user-agent': 'Kyheo SubsDown v0.1',
          'in-dir': '', # Full path to in dir 
          'out-dir': '', # Full path to out dir
          'log-level': logging.DEBUG,
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


def main(config):
    files = os.listdir(config['in-dir'])
    if not files:
        log.debug('No files, ending')
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


if __name__ == '__main__':
    main(config)
