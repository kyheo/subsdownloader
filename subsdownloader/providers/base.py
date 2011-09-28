
class Provider(object):

    NAME = 'Undefined'

    def search(self, file_, languages):
        raise NotImplementedError('Must redefine search in Provider')

    def close(self):
        raise NotImplementedError('Must redefine close in Provider')


class Subtitle(object):

    def __init__(self, provider, file_):
        self.provider = provider
        self.file_ = file_

        self.filename = None
        self.extension = None

    def save(self, path, name):
        raise NotImplementedError('Must redefine download in provider Subtitle')
