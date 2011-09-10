#! /usr/bin/env python
import logging

from src import options
from src import quota as quota_utils
from src import files as files_utils
from src import emails
from src import opensubtitles

def main(options):
    server = opensubtitles.Server(options)
    server.connect()

    excluded_subs = files_utils.get_excluded_subs(options)
    
    quota = quota_utils.Quota(options)

    downloaded = []
    for file_ in files_utils.MediaFiles(options):
        logging.info('Processing %s', file_.filename)
        if quota.reached():
            logging.info('Quota reached, ending !.')
            break
        try:
            for lang in options.langs:
                logging.debug(' > Searching for %s language', lang)
                sub_downloaded = False
                for subtitle in server.search(lang, file_):
                    if subtitle.get_hash() in excluded_subs:
                        logging.debug('Buggy sub, next !')
                        # Lets try with next sub entry
                        continue
                    file_.save(subtitle.download(), subtitle.get_format())
                    quota.qty += 1
                    downloaded.append(file_.filename)
                    sub_downloaded = True
                    # Break for, don't want to loop over the next subs
                    break
                if sub_downloaded:
                    break
        except Exception,e:
            logging.exception(e)
            # Lets try with the next file if any.
            continue

    server.disconnect()

    if options.notify == True:
        emails.send_notification_email(options, downloaded)

    quota.save()


if __name__ == '__main__':
    opts = options.parse_options()
    logging.info('Starting')
    main(opts)
    logging.info('Ending')
