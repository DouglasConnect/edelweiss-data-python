"""Usage:
  edelweiss permissions <dataset-id>
        [--add-user=<email,modifier>]...
        [--remove-user=<email>]...
        [--add-group=<name,modifier>]...
        [--remove-group=<email>]...

Options:
  -h --help      Show this screen

  --add-user=<email,modifier>
        Add a user who can read this dataset.
        The optional modifier can be 'ro' for read-only or 'rw' for 'read-write'.
        Modifier default is ro.
        E.g. --add-user=someone@example.com,rw

  --remove-user=<email>
        Remove a user's access permissions for this dataset

  --add-group=<name,modifier>
        Add a user group who can read this dataset.
        The optional modifier can be 'ro' for read-only or 'rw' for 'read-write'.
        Modifier default is ro.
        E.g. --add-group='my company'

  --remove-group=<name>
        Remove a user group's access permissions for this dataset

"""
from docopt import docopt
import json
from edelweiss_data import DatasetPermissions

def run(api, argv, pretty=False):
    args = docopt(__doc__, argv=argv)

    dataset_id = args['<dataset-id>']

    for item in args['--add-user']:
        parts = item.split(',')
        user = DatasetPermissions.User(
                email=parts[0],
                can_write=parts[1] == 'rw' if len(parts) > 1 else False,
                )
        api.add_dataset_user_permission(dataset_id, user)

    for email in args['--remove-user']:
        api.remove_dataset_user_permission(dataset_id, email)

    for item in args['--add-group']:
        parts = item.split(',')
        group = DatasetPermissions.Group(
                name=parts[0],
                can_write=parts[1] == 'rw' if len(parts) > 1 else False,
                )
        api.add_dataset_group_permission(dataset_id, group)

    for group in args['--remove-group']:
        api.remove_dataset_group_permission(dataset_id, group)

    permissions = api.get_dataset_permissions(dataset_id)

    print(json.dumps(permissions.encode(), indent=2 if pretty else None))
