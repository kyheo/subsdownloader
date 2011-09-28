import glob
import os
import hashlib
import re
import shutil


def get_excluded_subs(options):
    excluded_subs = []
    if options.exclude_subs:
        for file in os.listdir(options.exclude_subs):
            fp = open(os.path.join(options.exclude_subs, file), 'r')
            h = hashlib.md5()
            h.update(fp.read())
            fp.close()
            excluded_subs.append(h.hexdigest())
    return excluded_subs


class MediaFile(object):
    '''Media file'''

    def __init__(self, path, options):
        self.options = options
        self.path = path
        self.dir, self.filename = os.path.split(self.path)
        self.name, self.ext = os.path.splitext(self.filename)

    def __repr__(self):
        return self.path

    def save(self, sub_body, sub_format):
        # Create out dirs
        out_dir = getattr(self.options, 'dest', self.dir)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        # Move media file to dest dir
        dst_file = os.path.join(out_dir, self.filename)
        shutil.move(self.path, dst_file)
        # Save subtitle file
        self._save_subtitle(sub_body, sub_format, out_dir)

    def _save_subtitle(self, body, format_, out_dir):
        fname = '%s.%s' % (self.name, format_)
        dst_sub_name = os.path.join(out_dir, fname)
        fp = open(dst_sub_name, 'wb')
        fp.write(body)
        fp.close()

 
class MediaFiles(object):
    '''Files iterator'''

    def __init__(self, options):
        self.options = options
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
        exclude_regex = []
        for pattern in self.options.exclude:
            exclude_regex.append(re.compile(pattern))
        if self.options.regex:
            for regex in self.options.regex:
                for file_ in glob.glob(regex):
                    if os.path.isfile(file_):
                        file_list.append(file_)
        else:
            for root, dirs, files in os.walk(self.options.source):
                for file_ in files:
                    match = False
                    fname = os.path.join(root, file_)
                    for reg_exp in exclude_regex:
                        if reg_exp.search(fname):
                            match = True
                            break
                    if not match:
                        file_list.append(fname)

                if not self.options.recursive:
                    break

        return [MediaFile(file_, self.options) for file_ in file_list]
