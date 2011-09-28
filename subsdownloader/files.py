import os
import shutil

class MediaFiles(object):
    '''Files iterator'''

    def __init__(self, source, recursive=False):
        self.source = source
        self.recursive = recursive
        self.index = 0
        self.data = self._load()

    def __iter__(self):
        return self

    def next(self):
        if self.index == len(self.data):
            raise StopIteration
        entry = self.data[self.index]
        self.index += 1
        return entry

    def _load(self):
        file_list = []
        for root, dirs, files in os.walk(self.source):
            for file_ in files:
                fname = os.path.join(root, file_)
                file_list.append(fname)

            if not self.recursive:
                break

        return [MediaFile(file_) for file_ in file_list]



class MediaFile(object):
    '''Media file'''

    def __init__(self, path):
        self.path = path
        self.dir, self.filename = os.path.split(self.path)
        self.name, self.ext = os.path.splitext(self.filename)

    def __repr__(self):
        return self.path

    def save(self, path):
        if not os.path.exist(path):
            os.makedirs(path)
        new_path = os.path.join(path, self.filename)
        shutil.move(self.path, new_path)
