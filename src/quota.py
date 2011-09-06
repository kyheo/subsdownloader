import logging
import json
import datetime


class Quota(object):
    def __init__(self, options):
        super(Quota, self).__init__()
        self.options = options
        self.date = None
        self.qty = 0
        self.initialize()

    def initialize(self):
        try:
            logging.debug('Loading quota information')
            fp = open(self.options.quota_file, 'r')
            data = json.load(fp)
            fp.close()
            self.qty = data['qty']
            self.date = datetime.datetime.strptime(data['date'], '%Y-%m-%d')
            self.date = self.date.date()
        except IOError:
            logging.debug('  No quota file, creating one')
            self.save()

    def reached(self):
        today = datetime.date.today()
        if self.date == today and self.qty >= self.options.quota_limit:
            return True
        return False
    
    def save(self):
        data = {'date': datetime.date.today().isoformat(),
                'qty': self.qty}
        fp = open(self.options.quota_file, 'w')
        json.dump(data, fp)
        fp.close()



