"""Usage: edelweiss authenticate [--refresh-token]

Prints an access token for authenticating to the edelweiss API.

Options:
  -h --help          Show this screen
  --refresh-token    Print a refresh token instead of an access token

"""
from docopt import docopt

def run(api, argv):
    args = docopt(__doc__, argv=argv)
    if not api.auth:
        print("Authentication command is incompatible with your authentication options")
        exit(1)
    if args['--refresh-token']:
        print(api.auth.refresh_token)
    else:
        print(api.auth.jwt)
