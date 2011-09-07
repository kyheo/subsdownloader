import logging
import xmlrpclib
import base64
import cStringIO
import gzip

from src import files as files_utils

class Server(object):

    def __init__(self, options):
        self.options = options
        self.server = None
        self.token = None


    def connect(self):
        self.server = xmlrpclib.Server(self.options.api_url);
        login = self.server.LogIn('', '', '', self.options.api_user_agent)
        if login['status'] == '200 OK':
            raise Exception("Couldn't login.")
        self.token = login['token']


    def disconnect(self):
        logout = self.server.LogOut(self.token)
        if logout['status'] != '200 OK':
            # We won't throw an exception because the script ended "properly".
            logging.error("Error when logging out.")


    def search(self, lang, file_):
        hash_, size = files_utils.hashFile(file_)
        data = self.server.SearchSubtitles(self.token, 
                                           [{'sublanguageid': lang,
                                             'moviehash': str(hash_), 
                                             'moviebytesize': str(size)}])
        return data


    def download(self, sub_id):
        sub_data = self.server.DownloadSubtitles(self.token, [sub_id])
        sub_content = base64.b64decode(sub_data['data'][0]['data']) 
        sf_data = cStringIO.StringIO(sub_content)
        return gzip.GzipFile('', 'r', 0, sf_data).read()

