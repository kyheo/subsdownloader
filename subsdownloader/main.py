import logging

from subsdownloader.options import parse_options
from subsdownloader import files
from subsdownloader import providers
from subsdownloader import utils

def main():
    options = parse_options()
    
    file_list = files.MediaFiles(options.source, options.recursive)
    if not file_list:
        logging.info('No files found.')
        return

    provider_list = providers.init()

    for file_ in file_list:
        logging.info('Searching subs for %s', file_.filename)
        subtitles = []

        for provider in provider_list:
            logging.debug('> Querying %s', provider.NAME)
            subtitles += provider.search(file_, options.languages)

        subtitles = utils.sort_subtitles(subtitles)
        for subtitle in subtitles:
            try:
                logging.debug('>> Downloading Subtitle')
                subtitle.save(options.destination, file_.name)
                file_.save(options.destination)
                break
            except:
                pass

    providers.terminate()


if __name__ == '__main__':
    main()
