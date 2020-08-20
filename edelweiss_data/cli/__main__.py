"""Edelweiss Data CLI

A CLI tool for EdelweissData: Convenient publishing of scientific data with proper versioning, rich metadata support and a powerful API.

Usage:
    edelweiss (-h | --help)
    edelweiss [options] authenticate [<args>...]
    edelweiss [options] create [<args>...]
    edelweiss [options] published list [<args>...]
    edelweiss [options] published get [<args>...]
    edelweiss [options] published delete [<args>...]
    edelweiss [options] published new-version [<args>...]
    edelweiss [options] inprogress get [<args>...]
    edelweiss [options] inprogress delete [<args>...]
    edelweiss [options] inprogress update [<args>...]
    edelweiss [options] inprogress publish [<args>...]
    edelweiss [options] permissions [<args>...]

General options:
  -h --help          Show this screen
  --url=URL          The base edelweiss api url [default: https://api.edelweissdata.com]
  --pretty           Use pretty formatting for JSON outputs

Authentication options:
  --token-dir=<dir>  The directory in which to store refresh tokens
  --anonymous        Skip authentication and view only public resources.
  --no-cache-token   Skip caching the authentication token to the `token-dir`
  --refresh-token=<token>
                     Use the provided refresh token instead of the default authentication flow
  --scopes=<scopes>  Any additional authentication scopes to request from the authentication server, comma separated

Help:
    Use the --help option for more details on any sub-command:
    edelweiss published list --help

Examples:
    edelweiss --pretty --anonymous published list --search-anywhere=covid
"""
from docopt import docopt
from edelweiss_data import API
import json

def main():

    args = docopt(__doc__, version="0.1.0", options_first=True)

    if '--help' in args['<args>']:
        # skips setup requests if the subcommand doees not need the api
        api = None
    else:
        api = API(args['--url'])
        if not args['--anonymous']:
            scopes = (args['--scopes'] or '').split(',')
            api.authenticate(cache_jwt=(not args['--no-cache-token']), token_dir=args['--token-dir'],
                    refresh_token=args['--refresh-token'], scopes=scopes, lazy=True)

    if args['authenticate']:
        from . import auth
        return auth.run(api, ['authenticate'] + args['<args>'])
    elif args['published']:
        if args['list']:
            from . import published_list
            return published_list.run(api, ['published', 'list'] + args['<args>'], pretty=args['--pretty'])
        if args['get']:
            from . import published_get
            return published_get.run(api, ['published', 'get'] + args['<args>'], pretty=args['--pretty'])
        if args['delete']:
            from . import published_delete
            return published_delete.run(api, ['published', 'delete'] + args['<args>'], pretty=args['--pretty'])
        if args['new-version']:
            from . import published_newversion
            return published_newversion.run(api, ['published', 'new-version'] + args['<args>'], pretty=args['--pretty'])
    elif args['create']:
            from . import create
            return create.run(api, ['create'] + args['<args>'], pretty=args['--pretty'])
    elif args['inprogress']:
        if args['get']:
            from . import inprogress_get
            return inprogress_get.run(api, ['inprogress', 'get'] + args['<args>'], pretty=args['--pretty'])
        if args['delete']:
            from . import inprogress_delete
            return inprogress_delete.run(api, ['inprogress', 'delete'] + args['<args>'], pretty=args['--pretty'])
        if args['update']:
            from . import inprogress_update
            return inprogress_update.run(api, ['inprogress', 'update'] + args['<args>'], pretty=args['--pretty'])
        if args['publish']:
            from . import inprogress_publish
            return inprogress_publish.run(api, ['inprogress', 'publish'] + args['<args>'], pretty=args['--pretty'])
    elif args['permissions']:
            from . import permissions
            return permissions.run(api, ['permissions'] + args['<args>'], pretty=args['--pretty'])

if __name__ == "__main__":
    main()
