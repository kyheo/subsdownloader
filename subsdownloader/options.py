import optparse
import logging


def parse_options():
    usage = 'usage: %prog [options] source\n' \
        '   source is the directory where the media files are located'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False, help='Show more information as possible.')
    parser.add_option("-y", action="store_true", dest="vverbose", default=False, help='Show as much information as possible.')
    parser.add_option('-r', dest='recursive', action='store_true', default=False, help='Recurse subdirectories.')
    parser.add_option('-l', type='string', dest='languages', metavar='LANG', action='append', default=[], help='Subtitle download language. (Can be used multiple times).')
    parser.add_option('-d', type='string', dest='destination', metavar='DEST', help='Destination directory. Default to source one.')

    (options, args) = parser.parse_args()

    if not args or len(args) > 1:
        parser.error('You must provide one source.')
    options.source = args[0]

    if not options.languages:
        parser.error('You must provide at least one language option.')
    options.languages = remove_dups(options.languages)

    if options.vverbose is True:
        log_level = logging.DEBUG
    elif options.verbose is True:
        log_level = logging.INFO
    else:
        log_level = logging.ERROR

    logging.basicConfig(level=log_level, datefmt='%Y-%m-%d %H:%M:%S',
#        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s',
        format='%(levelname)8s - %(filename)s:%(lineno)s - %(message)s',
        )

    return options



# These functions were borrowed from here
# http://www.peterbe.com/plog/uniqifiers-benchmark
# The functions here are f11 and _f11 from Update section
def remove_dups(seq):
    # Order preserving
    return list(_remove_dups_helper(seq))

def _remove_dups_helper(seq):
    seen = set()
    for x in seq:
        if x in seen:
            continue
        seen.add(x)
        yield x
