import logging
import re
import glob
import os
import struct
import hashlib

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
