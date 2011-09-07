#! /usr/bin/env python
import os
import shutil

import logging

from src import options
from src import quota as quota_utils
from src import files as files_utils
from src import emails
from src import opensubtitles

def main(options):
    quota = quota_utils.Quota(options)
    if quota.reached():
        logging.error('Quota reached, ending !.')
        return

    files = files_utils.get_filenames(options)
    if not files:
        logging.info('No files, ending')
        return

    excluded_subs = files_utils.get_excluded_subs(options)
    
    server = opensubtitles.Server(options)
    server.connect()

    #Search
    downloaded = []
    for file_ in files:
        logging.info('Processing ' + file_)
        try:
            data = server.search(options.lang, file_)
        except Exception,e:
            logging.exception(e)
            # Lets try with the next file if any.
            continue

        if data['data']:
            for d in data['data']:
                if d['SubHash'] in excluded_subs:
                    logging.debug('Buggy sub, next !')
                    continue
                try:
                    if quota.reached():
                        logging.info('Quota reached, ending')
                        break
                    # TODO: Catch exceptions individually
                    dirs, fname = os.path.split(file_)
                    filename, fileext = os.path.splitext(fname)
                    
                    sub_fname = '%s.%s' % (filename, d['SubFormat'])

                    # Download subtitle
                    logging.info('Downloading %s' % (sub_fname,))
                    body = server.download(d['IDSubtitleFile'])

                    # Create output dir
                    if options.dest:
                        out_dirs = options.dest
                    else:
                        out_dirs = dirs
 
                    if not os.path.exists(out_dirs):
                        logging.debug('Creating out directory')
                        os.makedirs(out_dirs)

                    # Move video file 
                    dst_file = os.path.join(out_dirs, fname)
                    shutil.move(file_, dst_file)
                    quota.qty += 1
                    downloaded.append(sub_fname)

                    # Write subtitle file
                    dst_sub_name = os.path.join(out_dirs, sub_fname)
                    fp = open(dst_sub_name, 'wb')
                    fp.write(body)
                    fp.close()

                    # Break for, don't want to loop over the next subs
                    break
                except Exception, e:
                    logging.exception(e)
        else:
            logging.debug('Nothing found')

    #LogOut
    server.disconnect()

    #Send notification email
    if options.notify == True:
        logging.debug('Sending notification email')
        emails.send_notification_email(options, downloaded)

    quota.save()


if __name__ == '__main__':
    opts = options.parse_options()
    logging.info('Starting')
    main(opts)
    logging.info('Ending')
