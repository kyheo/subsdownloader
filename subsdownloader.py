#! /usr/bin/env python
import os
import shutil
import base64
import xmlrpclib
import cStringIO
import gzip

import logging

from src import options
from src import quota as quota_lib
from src import files as files_utils
from src import emails


def main(options):
    quota = quota_lib.Quota(options)
    if quota.reached():
        logging.info('Quota reached, ending')
        return

    files = files_utils.get_filenames(options) 
    if not files:
        logging.info('No files, ending')
        return

    excluded_subs = files_utils.get_excluded_subs(options)

    server = xmlrpclib.Server(options.api_url);
    login = server.LogIn('', '', '', options.api_user_agent)
    if login['status'] == '200 OK':
        token = login['token']
        logging.debug('Logged in with token %s' % (token,))
    else:
        logging.error('Couldn\'t log in.')
        return

    #Search
    downloaded = []
    for file in files:
        try:
            logging.info('Processing ' + file)
            hash, size = files_utils.hashFile(file)
            data = server.SearchSubtitles(token, [{'sublanguageid': options.lang, 
                                                   'moviehash': str(hash), 
                                                   'moviebytesize': str(size)}])
        except Exception,e:
            logging.error(str(e))
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
                    dirs, fname = os.path.split(file)
                    filename, fileext = os.path.splitext(fname)
                    
                    sub_fname = '%s.%s' % (filename, d['SubFormat'])

                    # Download subtitle
                    logging.info('Downloading %s' % (sub_fname,))
                    sub_data = server.DownloadSubtitles(token,
                                                        [d['IDSubtitleFile']])
                    sub_content = base64.b64decode(sub_data['data'][0]['data']) 
                    sf_data = cStringIO.StringIO(sub_content)
                    body = gzip.GzipFile('', 'r', 0, sf_data).read()

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
                    shutil.move(file, dst_file)
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
                    logging.error(str(e))
        else:
            logging.debug('Nothing found')

    #LogOut
    logout = server.LogOut(token)
    if logout['status'] == '200 OK':
        logging.debug('Logged out')

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
