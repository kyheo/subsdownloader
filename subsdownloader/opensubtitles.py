import logging
import xmlrpclib
import base64
import cStringIO
import gzip
import struct
import os

#quota_group = optparse.OptionGroup(parser, 'Quota options')
#quota_group.add_option('--quota-file', type='string', dest='quota_file', default='/tmp/quota-file.json', help='Track file for quota limits. Should persist over time.')
#quota_group.add_option('--quota-limit', type='int', dest='quota_limit', default=200, help='Max number of allowed downloads. Change this at your own risk.')
#parser.add_option_group(quota_group)

# Hardcoded values, shouldn't change at all
#options.api_url = 'http://api.opensubtitles.org/xml-rpc'
#options.api_user_agent = 'Kyheo SubsDown v0.1'

class Subtitle(object):

    def __init__(self, data, server):
        self.data = data
        self.server = server

    def download(self):
        return self.server.download(self.data['IDSubtitleFile'])

    def get_format(self):
        return self.data['SubFormat']

    def get_hash(self):
        return self.data['SubHash']

    def __repr__(self):
        return self.data['SubFileName']


class Server(object):

    def __init__(self, options):
        self.options = options
        self.server = None
        self.token = None

    def connect(self):
        self.server = xmlrpclib.Server(self.options.api_url);
        login = self.server.LogIn('', '', '', self.options.api_user_agent)
        if login['status'] != '200 OK':
            raise Exception("Couldn't login.")
        self.token = login['token']

    def disconnect(self):
        logout = self.server.LogOut(self.token)
        if logout['status'] != '200 OK':
            # We won't throw an exception because the script ended "properly".
            logging.error("Error when logging out.")

    def search(self, lang, file_):
        subtitles = []
        hash_, size = self.hashFile(file_.path)
        data = self.server.SearchSubtitles(self.token, 
                                           [{'sublanguageid': lang,
                                             'moviehash': str(hash_), 
                                             'moviebytesize': str(size)}])
        if data['data']:
            for d in data['data']:
                subtitles.append(Subtitle(d, self))
        return subtitles

    def download(self, sub_id):
        sub_data = self.server.DownloadSubtitles(self.token, [sub_id])
        sub_content = base64.b64decode(sub_data['data'][0]['data']) 
        sf_data = cStringIO.StringIO(sub_content)
        return gzip.GzipFile('', 'r', 0, sf_data).read()

    def hashFile(self, name):
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
