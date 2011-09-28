import logging
import xmlrpclib
import base64
import cStringIO
import gzip
import struct
import os


from subsdownloader.providers import base



class Connection(base.Provider):

    NAME = 'OpenSubtitles.org'
    URL = 'http://api.opensubtitles.org/xml-rpc'
    USER_AGENT = 'Kyheo SubsDown v0.1'

    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        self.server = None
        self.token = None


    def search(self, file_, languages):
        subtitles = []

        if self.server is None:
            self._connect()

        hash_, size = self._hash_file(file_.path)
        for language in languages:
            search_doc= [{'sublanguageid': language,
                          'moviehash': str(hash_), 
                          'moviebytesize': str(size)}]
            logging.debug(search_doc)
            data = self.server.SearchSubtitles(self.token, search_doc)
            logging.debug(data)
            if data['data']:
                for d in data['data']:
                    subtitles.append(Subtitle(self, file_, d))

        return subtitles


    def close(self):
        if self.server is not None:
            logout = self.server.LogOut(self.token)
            if logout['status'] != '200 OK':
                logging.error("Error when logging out.")


    def _connect(self):
        self.server = xmlrpclib.Server(Connection.URL);
        login = self.server.LogIn('', '', '', Connection.USER_AGENT)
        if login['status'] != '200 OK':
            raise Exception("Couldn't login.")
        self.token = login['token']


    def _hash_file(self, name):
        """Opensubtitles hash function modified to return not only the hash but
        also the file size.
        http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes#Python
        """
        longlongformat = 'q'  # long long 
        bytesize = struct.calcsize(longlongformat) 
            
        f = open(name, "rb") 
            
        filesize = os.path.getsize(name) 
        hash_ = filesize 
            
        if filesize < 65536 * 2: 
            raise Exception("SizeError")
         
        for x in range(65536/bytesize): 
            buffer_ = f.read(bytesize) 
            (l_value,)= struct.unpack(longlongformat, buffer_)  
            hash_ += l_value 
            hash_ = hash_ & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number  

        f.seek(max(0,filesize-65536),0) 
        for x in range(65536/bytesize): 
            buffer_ = f.read(bytesize) 
            (l_value,)= struct.unpack(longlongformat, buffer_)  
            hash_ += l_value 
            hash_ = hash_ & 0xFFFFFFFFFFFFFFFF 
         
        f.close() 
        returnedhash =  "%016x" % hash_ 
        return returnedhash, filesize 




class Subtitle(base.Subtitle):

    def __init__(self, data, *args, **kwargs):
        super(Subtitle, self).__init__(*args, **kwargs)
        self.data = data
        self.extension = self.data['SubFormat']
        self.filename = self.data['SubFileName']

    def __repr__(self):
        return self.data['SubFileName']

    def save(self, path, name):
        body = self._download()
        if not os.path.exist(path):
            os.makedirs(path)
        new_path = os.path.join(path, name) + '.' + self.extension
        fp = open(new_path, 'wb')
        fp.write(body)
        fp.close()

    def _download(self):
        sub_id = self.data['IDSubtitleFile']
        sub_data = self.server.DownloadSubtitles(self.token, [sub_id])
        sub_content = base64.b64decode(sub_data['data'][0]['data']) 
        sf_data = cStringIO.StringIO(sub_content)
        return gzip.GzipFile('', 'r', 0, sf_data).read()
