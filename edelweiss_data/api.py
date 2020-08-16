import pandas
import iso8601
import io
import datetime
from typing import Callable, Iterable, Any, Tuple, Dict, Union, Optional, TextIO, List, cast, Generator
import json

from . import server, utils

CLIENT_API_VERSION = '0.1.0'


class API(server.Server):
    '''The central interaction point with EdelweissData. You instantiate this class with the base url of the
          EdelweissData server you want to interact with. The __init__ method will verify that the server is reachable
          and speaks a compatible API version, then you can use instance methods to interact with the API server.
    '''

    def __init__(self, *args, fetch_batch_size:int=1000, **kwargs):
        '''Initializes an instance of the API class that let's you communicate with an EdelweissData server.

        :param base_url: Base url of the EdelweissData API server to communicate with
        '''
        super().__init__(*args, **kwargs)
        self.fetch_batch_size = fetch_batch_size
        server_api_version = self.get('/version')
        utils.ensure_compatible_versions(CLIENT_API_VERSION, server_api_version)
        self.get('/health')
        self.get('/ready')

    def _fetch_in_batches(self, fetch : Callable[[Optional[int], Optional[int]], Any], limit: Optional[int], offset: Optional[int]) -> Iterable[Any]:
        start = 0 if offset is None else offset
        end = None if limit is None else limit + start
        batch_size = self.fetch_batch_size
        while True:
            # First, we determine how much data to fetch in the next request
            # If there is no end, we take the default
            if end is None:
                pass
            # If there is an end, we continue fetching until we reach it
            elif start < end:
                batch_size = min(batch_size, end - start)
            # If we're past the end, we stop
            else:
                return
            # We fetch the response, and if we got anything, we repeat the loop
            try:
                response = fetch(batch_size, start)
            except server.EdelweissHttpError as error:
                if error.error_type == "TooMuchDataRequested":
                    # Try again with a smaller fetch size
                    batch_size = round(batch_size * 0.2)
                    if batch_size > 0:
                        continue
                raise error
            if response:
                start += batch_size
                yield response
            else:
                return

    def openapi_documents(self) -> List[str]:
        '''Returns a list of all dataset specific openapi descriptions (i.e. one openapi document for each dataset with the
             precise Json Schema of the particular datasets data endpoint).

        :returns: A list of url strings at which to retrieve the openapi.json documents for the documents
        '''
        return cast(List[str], self.get('/openapidocuments'))

    def openapi(self) -> Dict[str, Any]:
        '''Returns the OpenAPI definition of the entire EdelweissData REST API.

        :returns: The OpenAPI definition as a dict'''
        return cast(Dict[str, Any] , self.get('/openapi.json'))

    def get_in_progress_datasets(self, limit: Optional[int]=None, offset: Optional[int]=None) -> List["InProgressDataset"]:
        '''Returns a list of all in-progress datasets you are allowed to access (needs authentication).

        :returns: a list of InProgressDatasets

        :param limit: Number of datasets to retrieve - if None (default) it will retrieve all.
        :param offset: Starting offset from which to retrieve the datasets
        '''
        route = '/datasets/in-progress'
        def fetch(limit: Optional[int], offset: Optional[int]):
            request = {'limit': limit, 'offset': offset}
            return self.get(route, json=request)
        datasets = []
        for batch in self._fetch_in_batches(fetch, limit, offset):
            datasets += [InProgressDataset.decode(d, api=self) for d in batch]
        return datasets

    def get_in_progress_dataset(self, id: str) -> "InProgressDataset":
        '''Returns an in-progress datasets with a given id.

        :returns: an InProgressDataset

        :param id: the id of the dataset to retrieve'''
        route = '/datasets/{}/in-progress'.format(id)
        return InProgressDataset.decode(self.get(route), api=self)

    def create_in_progress_dataset(self, name: str) -> "InProgressDataset":
        '''Creates a new in-progress dataset on the server and returns it.

        :returns: The InProgressDataset that was created.

        :param name: the name of the dataset to create'''
        route = '/datasets/create'
        return InProgressDataset.decode(self.post(route, {'name': name}), api=self)

    def get_raw_datasets(self, columns: Optional[Iterable[Tuple[str,str]]]=None, condition: Optional["QueryExpression"] =None, include_description: Optional[bool]=None, include_schema: Optional[bool]=None, include_metadata: Optional[bool]=None, include_aggregations: Optional[bool]=None, aggregation_filters:Optional[Dict[str, Iterable[str]]]=None, limit:Optional[int]=None, offset:Optional[int]=None, order_by:Optional[List["QueryExpression"]]=None, ascending:Union[bool, List[bool]]=True, latest_only: Optional[bool]=None) -> Any:
        '''Get the published datasets. Unlike the more high-level get_published_datasets this method
             does not create a dataframe but returns the raw list of dicts representing the json response.
             Unless explicity included the fields schema, metadata and description will not be included
             in the response.

        :returns: The published datasets as a list of dicts (raw json response)

        :param columns: a list of pairs (column_name, json_path) describing
          columns in the dataframe.
        :param condition: a QueryExpression object limiting the fetched datasets.
        :param include_description: a boolean specifying if the datasets in
          the response should include the description
        :param include_schema: a boolean specifying if the datasets in
          the response should include the schema
        :param include_metadata: a boolean specifying if the datasets in
          the response should include the metadata
        :param aggregation_filters: a dict limiting the fetched datasets to ones
          where column values fall into one of the selected aggregation buckets.
          For example, using the dict
            {'organ': ['liver', 'kidney'], 'species': ['mouse', 'elephant']}
          would return the datasets where both organ is either liver or kidney,
          AND species is either mouse or elephant.
        :param limit: the number of rows to return (default 100).
          Returns all rows if set to None.
        :param offset: the initial offset (default 0).
        :param order_by: a list of QueryExpression objects by which to order
          the resulting datasets.
        :param ascending: a boolean or list of booleans to select the ordering.
          If the single boolean is True (the default), the list is ascending
          according to order_by, if False, it is descending. If given as a list,
          it must be of the same length as the order_by list, and the order is
          the ascending/descending for each particular component.
        :param latest_only: a boolean specifying whether to return only the latest
          version of each dataset
        '''
        route = '/datasets'
        request: Dict[str, Any] = {}
        if columns is not None:
            request['columns'] = [
                {
                    'name': column[0],
                    'jsonPath': column[1],
                }
                for column in columns
            ]
        if condition is not None:
            request['condition'] = condition.encode()
        if include_description is not None:
            request['includeDescription'] = include_description
        if include_schema is not None:
            request['includeSchema'] = include_schema
        if include_metadata is not None:
            request['includeMetadata'] = include_metadata
        if include_aggregations is not None:
            request['includeAggregations'] = include_aggregations
        if aggregation_filters is not None:
            request['aggregationFilters'] = utils.encode_aggregation_filters(aggregation_filters)
        if offset is not None:
            request['offset'] = offset
        if limit is not None:
            request['limit'] = limit
        if order_by is not None:
            request['orderBy'] = utils.encode_order_by(order_by, ascending)
        if latest_only is not None:
            request['latestOnly'] = latest_only
        return self.get(route, json=request)

    def get_published_datasets(self, columns: Optional[Iterable[Tuple[str,str]]]=None, condition: Optional["QueryExpression"] =None, include_description: Optional[bool]=None, include_schema: Optional[bool]=None, include_metadata: Optional[bool]=None, include_aggregations: Optional[bool]=None, aggregation_filters:Optional[Dict[str, Iterable[str]]]=None, limit:Optional[int]=None, offset:Optional[int]=None, order_by:Optional[List["QueryExpression"]]=None, ascending:Union[bool, List[bool]]=True, dataset_column_name: str='dataset', latest_only: Optional[bool]=None) -> pandas.DataFrame:
        '''Returns a dataframe of all published datasets that match query.

        :returns: a dataframe indexed by the id and version, which in addition
          to user-specified columns, contains a column with a PublishedDataset
          object for each dataset. Unless included explicitly, description, schema,
          and metadata are omitted from the datasets and the corresponding
          attributes are set to None. On the first access to any of the missing
          attributes of a given dataset, all three them are fetched from the server
          and set to the actual values, resulting in a single request for each dataset.
          If there are many datasets for which the attributes are required, it makes
          sense to include the content in the bulk request.

        :param columns: a list of pairs (column_name, json_path) describing
          the name of the new column to generate and which jsonpath to use to
          extract the values from the metadata to fill this column.
        :param condition: a QueryExpression object limiting the fetched datasets.
        :param include_description: a boolean specifying if the datasets in
          the response should include the description
        :param include_schema: a boolean specifying if the datasets in
          the response should include the schema
        :param include_metadata: a boolean specifying if the datasets in
          the response should include the metadata
        :param aggregation_filters: a dict limiting the fetched datasets to ones
          where column values fall into one of the selected aggregation buckets.
          For example, using the dict
            {'organ': ['liver', 'kidney'], 'species': ['mouse', 'elephant']}
          would return the datasets where both organ is either liver or kidney,
          AND species is either mouse or elephant.
        :param limit: the number of rows to return.
          Returns all rows if set to None (default).
        :param offset: the initial offset (default 0).
        :param order_by: a list of QueryExpression objects by which to order
          the resulting datasets.
        :param ascending: a boolean or list of booleans to select the ordering.
          If the single boolean is True (the default), the list is ascending
          according to order_by, if False, it is descending. If given as a list,
          it must be of the same length as the order_by list, and the order is
          the ascending/descending for each particular component.
        :param dataset_column_name: the name of the dataframe column in which
          the corresponding PublishedDataset objects are available.
        :param latest_only: a boolean specifying whether to return only the latest
          version of each dataset
        '''
        versions = []
        records = []
        def fetch(limit, offset):
            return self.get_raw_datasets(
                columns=columns,
                condition=condition,
                include_description=include_description,
                include_schema=include_schema,
                include_metadata=include_metadata,
                include_aggregations=False,
                aggregation_filters=aggregation_filters,
                limit=limit,
                offset=offset,
                order_by=order_by,
                ascending=ascending,
                latest_only=latest_only
            )['results']
        for results in self._fetch_in_batches(fetch, limit, offset):
            for result in results:
                record = result['columns']
                record[dataset_column_name] = PublishedDataset.decode(result, api=self)
                records.append(record)
                versions.append((result['id']['id'], result['id']['version']))
        index = pandas.MultiIndex.from_tuples(versions, names=['id', 'version'])
        column_names = [column[0] for column in columns] if columns else []
        if dataset_column_name is not None:
            column_names.insert(0, dataset_column_name)
        if records:
            return pandas.DataFrame.from_records(records, columns=column_names, index=index)
        else:
            return pandas.DataFrame(columns=column_names, index=index)

    def get_published_dataset_aggregations(self, columns:Optional[Iterable[Tuple[str,str]]]=None, condition: Optional["QueryExpression"]=None, aggregation_filters:Optional[Dict[str, Iterable[str]]]=None) -> pandas.Series:
        '''Returns aggregation buckets and their sizes for each column.

        :returns: aggregations as a Series with an index of buckets and terms, for example
            bucket     term
            organ      liver          10
                       kidney         20
            species    mouse           5
                       elephant       30
        :param columns: same as in self.get_published_datasets
        :param condition: same as in self.get_published_datasets
        :param aggregation_filters: same as in self.get_published_datasets
        '''
        response = self.get_raw_datasets(
            columns=columns,
            condition=condition,
            include_aggregations=True,
            aggregation_filters=aggregation_filters,
            limit=0,
        )
        return utils.decode_aggregations(response['aggregations'])

    def get_published_dataset(self, id: str, version:Optional[Union[str,int]]=None) -> "PublishedDataset":
        '''Returns a published dataset with a given id and version.

        :returns: the PublishedDataset

        :param id: id of the dataset to retrieve
        :param version: version of the dataset to retrieve. Defaults to LATEST if none specified.
        '''
        if version is None:
            version = PublishedDataset.LATEST
        route = '/datasets/{}/versions/{}'.format(id, version)
        return PublishedDataset.decode(self.get(route), api=self)

    def get_published_dataset_versions(self, id: str) -> List["PublishedDataset"]:
        '''Returns all published versions of dataset with a given id.

        :returns: a list of PublishedDatasets
        :param id: id of the dataset'''
        route = '/datasets/{}'.format(id)
        response = self.get(route)
        id, versions = response['id'], response['versions']
        return [
            PublishedDataset.decode({'id': id, 'version': version['version'], 'name': version['name']}, api=self)
            for version in versions
        ]

    def create_in_progress_dataset_from_csv_file(self, name: str, file: TextIO, metadata: dict = None) -> "InProgressDataset":
        '''Creates a new in-progress dataset from a CSV file on the server.

        :returns: the updated dataset
        :param name: the name of the dataset
        :param file: opened text file to read the csv data from
        :param metadata: dict of the metadata to store as json together with the dataset'''
        dataset = self.create_in_progress_dataset(name)
        dataset.upload_data(file)
        dataset.infer_schema()
        if metadata is not None:
            dataset.upload_metadata(metadata)
        return dataset

    def create_published_dataset_from_csv_file(self, *args, changelog: str='Initial version', **kwargs) -> "PublishedDataset":
        '''Creates a new published dataset from a CSV file on the server.

        :returns: the published dataset
        :param name: the name of the dataset
        :param file: opened text file to read the csv data from
        :param metadata: dict of the metadata to store as json together with the dataset
        :param changelog: Publishing message to store for the first version'''
        dataset = self.create_in_progress_dataset_from_csv_file(*args, **kwargs)
        published_dataset = dataset.publish(changelog)
        return published_dataset

    def get_dataset_permissions(self, dataset_id: str) -> "DatasetPermissions":
        '''Get the permissions for the given dataset id

        :returns: the DatasetPermissions instance for this dataset
        :param dataset_id: the id of the dataset
        '''
        route = '/datasets/{}/permissions'.format(dataset_id)
        return DatasetPermissions.decode(self.get(route))

    def add_dataset_user_permission(self, dataset_id: str, user: "DatasetPermissions.User"):
        '''Add a user to a dataset

        :param dataset_id: the id of the dataset
        :param user: the User to add
        '''
        route = '/datasets/{}/permissions/users/add'.format(dataset_id)
        return self.post(route, user.encode())

    def remove_dataset_user_permission(self, dataset_id: str, email: str):
        '''Remove a user from a dataset

        :param dataset_id: the id of the dataset
        :param user: the email of the user to remove
        '''
        route = '/datasets/{}/permissions/users/delete'.format(dataset_id)
        payload = {
            'email': email,
        }
        return self.post(route, payload)

    def add_dataset_group_permission(self, dataset_id: str, group: "DatasetPermissions.Group"):
        '''Add a group to a dataset

        :param dataset_id: the id of the dataset
        :param group: the Group to add
        '''
        route = '/datasets/{}/permissions/groups/add'.format(dataset_id)
        return self.post(route, group.encode())

    def remove_dataset_group_permission(self, dataset_id: str, name: str):
        '''Remove a group from a dataset

        :param dataset_id: the id of the dataset
        :param name: the name of the group to remove
        '''
        route = '/datasets/{}/permissions/groups/delete'.format(dataset_id)
        payload = {
            'name': name,
        }
        return self.post(route, payload)

    def change_dataset_visibility(self, dataset_id: str, is_public: bool):
        '''Set if the dataset should be public or access protected when published

        :param dataset_id: the id of the dataset
        :param is_public: boolean to indicate if the dataset should be public
        '''
        route = '/datasets/{}/permissions/visibility'.format(dataset_id)
        payload = {
            'isPublic': is_public,
        }
        return self.post(route, payload)

    def oidc_config(self):
        '''Returns the OpenID Connect configuration.'''
        return self.get('/oidc')



class Schema:
    '''The schema of the dataset describing the columns (name, description, datatype, rdf predicate, ...)

    '''
    class Column:
        '''The schema data of one column. This tells EdelweissData the name of the column, the datatype to use, how to handle missing values, ...
        '''
        def __init__(self, name: str, description: str, data_type: str, array_value_separator: str, missing_value_identifiers: Iterable[str], indices: List[str], rdf_predicate: str, statistics: Any, visible: bool):
            self.name = name
            self.description = description
            self.data_type = data_type
            self.array_value_separator = array_value_separator
            self.missing_value_identifiers = missing_value_identifiers
            self.indices = indices
            self.rdf_predicate = rdf_predicate
            self.statistics = statistics
            self.visible = visible

        def __repr__(self):
            return '<Column {}:{}>'.format(self.name, self.data_type)

        @classmethod
        def decode(cls, d):
            return cls(
                name=d['name'],
                description=d.get('description'),
                data_type=d['dataType'],
                array_value_separator=d.get('arrayValueSeparator'),
                missing_value_identifiers=d['missingValueIdentifiers'],
                indices=d.get('indices'),
                rdf_predicate=d.get('rdfPredicate'),
                statistics=d.get('statistics'),
                visible=d.get('visible'),
            )

        def encode(self):
            return {
                'name': self.name,
                'description': self.description,
                'dataType': self.data_type,
                'arrayValueSeparator': self.array_value_separator,
                'missingValueIdentifiers': self.missing_value_identifiers,
                'indices': self.indices,
                'rdfPredicate': self.rdf_predicate,
                'statistics': self.statistics,
                'visible': self.visible,
            }

    def __init__(self, columns: Iterable[Column]):
        self.columns = columns

    def __repr__(self):
        return '<Schema>'

    @classmethod
    def decode(cls, d):
        return cls(
            columns=[
                cls.Column.decode(column) for column in d['columns']
            ]
        )

    def encode(self):
        return {
            'columns': [column.encode() for column in self.columns]
        }


class DatasetPermissions:
    '''The permission information for a dataset. A list of users (email + flag if they can write), groups (name + flag if they can write) and
         an is_public field that indicates whether unauthenticated users can see this dataset when published.
    '''
    class User:
        def __init__(self, email: str, can_write: bool):
            self.email = email
            self.can_write = can_write

        @classmethod
        def decode(cls, u):
            return cls(email=u['email'], can_write=u['canWrite'])

        def encode(self):
            return {
                'email': self.email,
                'canWrite': self.can_write
            }

    class Group:
        def __init__(self, name: str, can_write: bool):
            self.name = name
            self.can_write = can_write

        @classmethod
        def decode(cls, g):
            return cls(name=g['name'], can_write=g['canWrite'])

        def encode(self):
            return {
                'name': self.name,
                'canWrite': self.can_write
            }

    def __init__(self, id: str, users: List[User], groups: List[Group], is_public: bool):
        self.id = id
        self.users = users
        self.groups = groups
        self.is_public = is_public

    def __repr__(self):
        return '<DatasetPermissions {!r}>'.format(self.id)

    @classmethod
    def decode(cls, dp):
        return cls(
            id=dp['id'],
            users=list(cls.User.decode(u) for u in dp['users']),
            groups=list(cls.Group.decode(g) for g in dp['groups']),
            is_public=dp['isPublic'],
        )

    def encode(self):
        return {
            'id': self.id,
            'isPublic': self.is_public,
            'users': list(u.encode() for u in self.users),
            'groups': list(g.encode() for g in self.groups),
        }







class InProgressDataset:
    '''InProgressDataset - datasets that are not yet published and for which data can be uploaded, the schema modified, metadata changed etc.
    '''
    def __init__(self, id: str, name: str, schema: Optional[Schema], created: datetime.datetime, description: str, metadata: dict, data_source: Optional["PublishedDataset"], api: "API"):
        self.id = id
        self.name = name
        self.schema = schema
        self.created = created
        self.description = description
        self.metadata = metadata
        self.data_source = data_source
        self.api = api

    def __repr__(self):
        return '<InProgressDataset {!r} - {}>'.format(self.id, self.name)

    @classmethod
    def decode(cls, d, api):
        return cls(
            id=d['id'],
            name=d['name'],
            schema=Schema.decode(d['schema']) if d['schema'] else None,
            created=iso8601.parse_date(d['created']),
            description=d['description'],
            metadata=d['metadata'],
            data_source=d.get('dataSource'),
            api=api
        )

    def encode(self):
        return {
            'id': self.id,
            'name': self.name,
            'schema': self.schema.encode() if self.schema else None,
            'created': self.created.isoformat(),
            'description': self.description,
            'metadata': self.metadata,
            'dataSource': self.data_source,
        }

    def sample(self) -> List[List[str]]:
        '''Retrieve a list of lists representing a sample of the tabular data of this dataset. This
            includes only a sample (e.g. the first N rows) of the data so that they can be displayed to a
            user as an example or similar.
        '''
        route = '/datasets/{}/in-progress/sample'.format(self.id)
        return cast(List[List[str]], self.api.get(route))

    def update(self, name: Optional[str] = None,
                     description: Optional[str] = None,
                     data_source: Optional['PublishedDataset'] = None,
                     schema: Optional[Schema] = None,
                     metadata: Optional[dict] = None):
        '''Update various attributes of a in-progress dataset. All parameters are options; those that are
        None will not have their values changed.

        :param name: A new name for the dataset
        :param description: A new description for the dataset
        :param data_source: A new data_source for the dataset. See set_data_source for a description of a data source.
        :param schema: A new schema for the dataset.
        :param metadata: A new metadata object for the dataset.
        '''
        route = '/datasets/{}/in-progress'.format(self.id)
        payload = {
            'name': name,
            'description': description,
            'dataSource': {'id': data_source.id, 'version': data_source.version} if data_source else None,
            'schema': schema.encode() if schema else None,
            'metadata': metadata,
        }
        updated_dataset = InProgressDataset.decode(self.api.post(route, json=payload), self.api)
        self.name = updated_dataset.name
        self.description = updated_dataset.description
        self.data_source = updated_dataset.data_source
        self.schema = updated_dataset.schema
        self.metadata = updated_dataset.metadata

    def upload_schema(self, schema: Schema):
        '''Upload a Schema (an instance of the class, not a file).

        :param schema: The schema to upload
        '''
        return self.update(schema=schema)

    def upload_schema_file(self, file: TextIO):
        '''Upload a schema file (an open text file containing the schema in Json form).

        :param file: The open text file to upload the schema from
        '''
        schema = Schema.decode(json.load(file))
        return self.update(schema=schema)

    def upload_metadata(self, metadata: dict):
        '''Upload metadata (as a dict, not a file).

        :param schema: The metadata to upload
        '''
        return self.update(metadata=metadata)

    def upload_metadata_file(self, file: TextIO):
        '''Upload a metadata file (an open text file containing the metadata in Json form).

        :param file: The open text file to upload the metadata from
        '''
        metadata = json.load(file)
        return self.update(metadata=metadata)

    def upload_data(self, data: TextIO):
        '''Upload tabular data (a CSV file)

        :param data: An open text file containing the csv data to upload
        '''
        route = '/datasets/{}/in-progress/data/upload'.format(self.id)
        return self.api.upload(route, {'data': data})

    def upload_dataframe_data(self, dataframe: pandas.DataFrame):
        '''Upload a pandas dataframe as the data content into an InProgress dataset

        :param dataframe: A Pandas dataframe containing the data to upload
        '''
        data = io.StringIO()
        dataframe.to_csv(data, index=False)
        data.seek(0)
        return self.upload_data(data)

    def set_description(self, description: str):
        '''Set the description of the dataset. The description is assumed to be markdown formatted text, similar to a Github README.md
        '''
        return self.update(description=description)

    def set_name(self, name: str):
        '''Set the name of the dataset.
        '''
        route = '/datasets/{}/in-progress'.format(self.id)
        self.api.post(route, json={'name': name})
        self.name = name

    def set_data_source(self, dataset: "PublishedDataset"):
        '''Set the data source for an in-progress dataset. This allows you to efficiently re-use the data of a PublishedDataset
            to create a new dataset without re-uploading the data. It is also useful if you want to create a new version of a
            PublishedDataset to fix a mistake in the metadata or description.

        :param dataset: the PublishedDataset to copy data from when publishing
        '''
        route = '/datasets/{}/in-progress'.format(self.id)
        data_source = PublishedDataset.decode({'id': dataset.id, 'version': dataset.version}, self.api)
        return self.update(data_source=data_source)

    def infer_schema(self):
        '''Triggers schema inference from uploaded data (this creates a schema on the server and sets it on the InProgressDataset)
        '''
        route = '/datasets/{}/in-progress/schema/infer'.format(self.id)
        updated_dataset = self.api.post(route, None)
        self.schema = Schema.decode(updated_dataset['schema'])

    def delete(self):
        '''Deletes the InProgressDataset
        '''
        route = '/datasets/{}/in-progress'.format(self.id)
        return self.api.delete(route)

    def publish(self, changelog: str) -> "PublishedDataset":
        '''Attempts to publish the dataset. This means that a new version of a PublishedDataset will be created (and returned by this call)
            and this InProgressDataset is no longer useable.

        '''
        route = '/datasets/{}/in-progress/publish'.format(self.id)
        return PublishedDataset.decode(self.api.post(route, {'changelog': changelog}), api=self.api)

    def copy_from(self, published_dataset: "PublishedDataset"):
        '''Copies all content from a PublishedDataset to this InProgressDataset. Useful to create new versions. See also set_data_source for
            a more lightweight operation if you don't need to change the data or schema structure.
        '''
        route = '/datasets/{}/in-progress/copy-from/{}/versions/{}'.format(
            self.id,
            published_dataset.id,
            published_dataset.version
        )
        return self.api.post(route)

    def get_permissions(self):
        return self.api.get_dataset_permissions(self.id)


class PublishedDataset:
    '''Represents a published dataset
    '''
    LATEST = 'LATEST'

    def __init__(self, id: str, version: int, name: str, schema: Optional[Schema], created: datetime.datetime, description: Optional[str], metadata: dict, row_count: Optional[int], is_public: bool, api: "API"):
        self.id = id
        self.version = version
        self.name = name
        self._schema = schema
        self.created = created
        self._description = description
        self._metadata = metadata
        self.row_count = row_count
        self._is_public = is_public
        self.api = api

    def __repr__(self):
        return '<PublishedDataset {!r}:{} - {}>'.format(self.id, self.version, self.name)

    def _fill_missing_fields(self):
        dataset = self.api.get_published_dataset(id=self.id, version=self.version)
        self._schema = dataset.schema
        self._description = dataset.description
        self._metadata = dataset.metadata
        self._is_public = dataset.is_public

    @property
    def schema(self) -> Optional[Schema]:
        '''Schema of this dataset. If this PublishedDatset instance was loaded from an API.get_published_datasets query and
             include_schema was not set to true then this property will be lazy loaded from the server when it is first accessed.
        '''
        if self._schema is None:
            self._fill_missing_fields()
        return self._schema

    @property
    def description(self) -> Optional[str]:
        '''Description text of this dataset. If this PublishedDatset instance was loaded from an API.get_published_datasets query and
             include_description was not set to true then this property will be lazy loaded from the server when it is first accessed.
        '''
        if self._description is None:
            self._fill_missing_fields()
        return self._description

    @property
    def metadata(self) -> Any:
        '''Metadata of this dataset. If this PublishedDatset instance was loaded from an API.get_published_datasets query and
             include_metadata was not set to true then this property will be lazy loaded from the server when it is first accessed.
        '''
        if self._metadata is None:
            self._fill_missing_fields()
        return self._metadata

    @property
    def is_public(self):
        '''Whether this dataset is public. If this PublishedDatset instance was loaded from an API.get_published_datasets query
             then this property will be lazy loaded from the server when it is first accessed.
        '''
        if self._is_public is None:
            self._fill_missing_fields()
        return self._is_public

    @classmethod
    def decode(cls, d, api):
        return cls(
            id=d['id']['id'],
            version=d['id']['version'],
            name=d['name'],
            schema=Schema.decode(d['schema']) if ('schema' in d and d['schema']) else None,
            created=iso8601.parse_date(d['created']),
            description=d.get('description'),
            metadata=d.get('metadata'),
            row_count=d['rowCount'] if 'rowCount' in d else d['rowcount'], # This handles a server-side bug which will be fixed in a future version.
            is_public=d.get('isPublic'),
            api=api
        )

    def encode(self):
        return {
            'id': {
                'id': self.id,
                'version': self.version,
            },
            'name': self.name,
            'schema': self.schema.encode() if self.schema else None,
            'created': self.created.isoformat(),
            'description': self.description,
            'metadata': self.metadata,
            'rowCount': self.row_count,
            'isPublic': self.is_public,
        }

    def new_version(self) -> "InProgressDataset":
        '''Create a new version of this PublishedDataset. This will create and return a new InProgressDataset
            that can be filled with content by uploading new files or copying data from a PublishedDataset

        :returns: The InProgressDataset
        '''
        route = '/datasets/{}/versions/{}/create-new-version'.format(self.id, self.version)
        return InProgressDataset.decode(self.api.post(route), api=self.api)

    def get_raw_data(self, columns: Optional[Iterable[str]]=None, condition: Optional["QueryExpression"]=None, include_aggregations: Optional[bool]=None, aggregation_filters:Optional[Dict[str, Iterable[str]]]=None, limit: Optional[int]=None, offset: Optional[int]=None, order_by: Optional[List["QueryExpression"]]=None, ascending:Union[bool, List[bool]]=True):
        '''Gets the raw tabular data JSON response for a PublishedDataset. The data can be filtered so that only required columns or rows
            are retrieved.

        :returns: A dict representing the JSON response
        :param columns: a list of column names that should appear in the result.
          If None, all columns are included.
        :param condition: a QueryExpression object limiting the fetched datasets.
        :param aggregation_filters: a dict limiting the fetched datasets to ones
          where column values fall into one of the selected aggregation buckets.
          For example, using the dict
            {'organ': ['liver', 'kidney'], 'species': ['mouse', 'elephant']}
          would return the datasets where both organ is either liver or kidney,
          AND species is either mouse or elephant.
        :param limit: the number of rows to return.
          Returns all rows if set to None (default).
        :param offset: the initial offset (default 0).
        :param order_by: a list of QueryExpression objects by which to order
          the resulting datasets.
        :param ascending: a boolean or list of booleans to select the ordering.
          If the single boolean is True (the default), the list is ascending
          according to order_by, if False, it is descending. If given as a list,
          it must be of the same length as the order_by list, and the order is
          the ascending/descending for each particular component.'''
        route = '/datasets/{}/versions/{}/data'.format(self.id, self.version)
        request: Dict[str, Any] = {}
        if columns is not None:
            request['columns'] = columns
        if condition is not None:
            request['condition'] = condition.encode()
        if include_aggregations is not None:
            request['includeAggregations'] = include_aggregations
        if aggregation_filters is not None:
            request['aggregationFilters'] = utils.encode_aggregation_filters(aggregation_filters)
        if offset is not None:
            request['offset'] = offset
        if limit is not None:
            request['limit'] = limit
        if order_by is not None:
            request['orderBy'] = utils.encode_order_by(order_by, ascending)
        return self.api.get(route, json=request)

    def get_data(self, columns: Optional[Iterable[str]]=None, condition: Optional["QueryExpression"]=None, aggregation_filters:Optional[Dict[str, Iterable[str]]]=None, limit: Optional[int]=None, offset: Optional[int]=None, order_by: Optional[List["QueryExpression"]]=None, ascending:Union[bool, List[bool]]=True) -> pandas.DataFrame:
        '''Gets the (tabular) data of a PublishedDataset as a pandas Dataframe. The data can be filtered so that only required columns or rows
            are retrieved.

        :returns: A pandas DataFrame with the tabular data
        :param columns: a list of column names that should appear in the result.
          If None, all columns are included.
        :param condition: a QueryExpression object limiting the fetched datasets.
        :param aggregation_filters: a dict limiting the fetched datasets to ones
          where column values fall into one of the selected aggregation buckets.
          For example, using the dict
            {'organ': ['liver', 'kidney'], 'species': ['mouse', 'elephant']}
          would return the datasets where both organ is either liver or kidney,
          AND species is either mouse or elephant.
        :param limit: the number of rows to return.
          Returns all rows if set to None (default).
        :param offset: the initial offset (default 0).
        :param order_by: a list of QueryExpression objects by which to order
          the resulting datasets.
        :param ascending: a boolean or list of booleans to select the ordering.
          If the single boolean is True (the default), the list is ascending
          according to order_by, if False, it is descending. If given as a list,
          it must be of the same length as the order_by list, and the order is
          the ascending/descending for each particular component.
        '''
        ids = []
        data = []
        def fetch(limit, offset):
            return self.get_raw_data(
                columns=columns,
                condition=condition,
                include_aggregations=False,
                aggregation_filters=aggregation_filters,
                limit=limit,
                offset=offset,
                order_by=order_by,
                ascending=ascending
            )['results']
        for results in self.api._fetch_in_batches(fetch, limit, offset):
            ids += [row['id'] for row in results]
            data += [row['data'] for row in results]
        column_names = [column.name for column in self.schema.columns]
        if data:
            return pandas.DataFrame.from_records(data, columns=column_names, index=ids)
        else:
            return pandas.DataFrame(columns=column_names, index=ids)

    def get_data_aggregations(self, columns:Optional[Iterable[str]]=None, condition:Optional["QueryExpression"]=None, aggregation_filters:Optional[Dict[str, Iterable[str]]]=None) -> pandas.Series:
        '''Returns aggregation buckets and their sizes for each column.

        :returns: aggregations as a Series with an index of buckets and terms, for example
            bucket     term
            organ      liver          10
                       kidney         20
            species    mouse           5
                       elephant       30
        :param columns: a list of column names that should appear in the result.
          If None, all columns are included.
        :param condition: a QueryExpression object limiting the fetched datasets.
        :param aggregation_filters: a dict limiting the fetched datasets to ones
          where column values fall into one of the selected aggregation buckets.
          For example, using the dict
            {'organ': ['liver', 'kidney'], 'species': ['mouse', 'elephant']}
          would return the datasets where both organ is either liver or kidney,
          AND species is either mouse or elephant.
        '''
        response = self.get_raw_data(
            columns=columns,
            condition=condition,
            include_aggregations=True,
            aggregation_filters=aggregation_filters,
            limit=0,
        )
        return utils.decode_aggregations(response['aggregations'])

    def openapi(self) -> Any:
        '''Returns a OpenAPI descriptions for the data endpoint of this PublishedDataset, taking the schema
            and thus the precise JSON structure of the response into account.

        :returns: A dict respresenting the JSON decoded OpenAPI document
        '''
        route = '/datasets/{}/versions/{}/openapi.json'.format(self.id, self.version)
        return self.api.get(route)

    def get_permissions(self):
        '''Returns the Permissions object of this PublishedDataset
        '''
        return self.api.get_dataset_permissions.get(self.id)

    def delete_all_versions(self):
        '''Deletes all versions of a published dataset
        '''
        route = '/datasets/{}'.format(self.id)
        self.api.delete(route)



class QueryExpression:
    '''Used to create filters or expressions to order records by. Use the classmethods on this
    class to create instances, e.g. QueryExpression.fuzzySearch(QueryExpression.column("species"), "Monkey")
    '''
    def __init__(self, *args):
        class_name = type(self).__name__
        if len(args) == 1:
            value = args[0]
            valid_types = [type(None), str, int, float, bool]
            if not any(isinstance(value, ty) for ty in valid_types):
                raise ValueError('Type {0} is not valid for a {1} constant'.format(type(value), class_name))
            else:
                self.is_node = False
                self.value = value
        elif len(args) == 2:
            name, arguments = args
            if not isinstance(name, str):
                raise ValueError('The first argument of a {0} node must be a string'.format(class_name))
            elif not (isinstance(arguments, list) and all(isinstance(argument, type(self)) for argument in arguments)):
                raise ValueError('The second argument of a {0} node must be a list of {0}s'.format(class_name))
            else:
                self.is_node = True
                self.name = name
                self.arguments = arguments
        else:
            raise TypeError('__init__ expected 1 (for constant) or 2 (for node) arguments, got {0}'.format(len(args)))

    def __repr__(self):
        if self.is_node:
            return '{0}({1!r}, {2!r})'.format(type(self).__name__, self.name, self.arguments)
        else:
            return '{0}({1!r})'.format(type(self).__name__, self.value)

    @classmethod
    def _convert_if_necessary(cls, value) -> "QueryExpression":
        if isinstance(value, cls):
            return value
        else:
            return cls(value)

    @classmethod
    def decode(cls, value) -> "QueryExpression":
        if isinstance(value, dict) and len(value) == 1:
            name, arguments = value.popitem()
            return cls(name, [cls.decode(argument) for argument in arguments])
        else:
            return cls(value)

    def encode(self):
        if self.is_node:
            return {self.name: [argument.encode() for argument in self.arguments]}
        else:
            return self.value

    @classmethod
    def search_anywhere(cls, term: str) -> "QueryExpression":
        '''Constructs a SearchAnywhere expression. Only rows will be returned that contain the search term in one of their text-like columns.

        :param term: The string to search for in all text-like columns.
        '''
        return cls('searchAnywhere', [cls(term)])

    @classmethod
    def column(cls, column_name: str) -> "QueryExpression":
        '''Constructs a Column expression.

        :param column_name: the name of the column
        '''
        return cls('column', [cls(column_name)])

    @classmethod
    def system_column(cls, column_name: str) -> "QueryExpression":
        '''Constructs a SystemColumn expression. SystemColumns are special columns maintained by EdelweissData.
            The following SystemColumns are available:
                name (text): the name of a dataset
                created (text/datetime): the timestamp the dataset was created at
                version: (int): the version number of the dataset

        :param column_name: the name of the column
        '''
        return cls('systemColumn', [cls(column_name)])

    @classmethod
    def exact_search(cls, expr: "QueryExpression", term: str) -> "QueryExpression":
        '''Constructs an ExactSearch expression. Only rows where the expr expression exactly matches the term will be returned. This can be used
            to match exact substrings or exact numerical values

        :param expr: the search expression to evaluate (often a column QueryExpression)
        :param term: the search term'''
        return cls('exactSearch', [expr, cls(term)])

    @classmethod
    def fuzzy_search(cls, expr: "QueryExpression", term: str) -> "QueryExpression":
        '''Constructs a FuzzySearch expression. Only rows where the expr expression fuzzy-matches the term will be returned. Fuzzy-matching
            uses trigram indexing to match slightly different spellings.

        :param expr: the search expression to evaluate (often a column QueryExpression)
        :param term: the search term
        '''
        return cls('fuzzySearch', [expr, cls(term)])

    @classmethod
    def substructure_search(cls, substructure: "QueryExpression", superstructure: "QueryExpression") -> "QueryExpression":
        '''Constructs a SubstructureSearch expression that uses chemical substructure testing. Only rows where the chemical substructure is contained in
            the chemical superstructure are returned.

        :param substructure: the substructure to search (often a SMILES string constant value)
        :param superstructure: the search term (often a Column of datatype SMILES)
        '''
        return cls('substructureSearch', [cls._convert_if_necessary(substructure), cls._convert_if_necessary(superstructure)])

    @classmethod
    def tanimoto_similarity(cls, left: "QueryExpression", right: "QueryExpression") -> "QueryExpression":
        '''Calculates the tanimoto distance between two molecular fingerprints.

        :param left: the left argument. Often a SMILES string constant value or Column of datatype SMILES.
        :param right: the right argument. Often a SMILES string constant value or Column of datatype SMILES.
        '''
        return cls('tanimotoSimilarity', [cls._convert_if_necessary(left), cls._convert_if_necessary(right)])

    @classmethod
    def cast(cls, expr: "QueryExpression", data_type: str) -> "QueryExpression":
        '''Creates a Cast expression. This attempts to convert one datatype into another.

        :param expr: The expression to cast
        :param data_type: The datatype to cast to
        '''
        return cls('cast', [expr, cls(data_type)])

    @classmethod
    def contains(cls, expr: "QueryExpression", element: "QueryExpression") -> "QueryExpression":
        '''Creates a Contains expression. Tests if an expression contains an element. Often used
            to check if columns of an Array datatype contain a value.

        :param expr: The expression to search in
        :param element: The element to search for
        '''
        return cls('contains', [expr, cls(element)])

    @classmethod
    def contained_in(cls, expr: "QueryExpression", element: "QueryExpression") -> "QueryExpression":
        '''Creates a ContainedIn expression. Tests if an expression is contained in an element. Often used
            to check if columns of an Array datatype are contained in a value.

        :param expr: The expression to search for
        :param element: The element to search in
        '''
        return cls('containedIn', [expr, cls(element)])

    def __getitem__(self, json_path):
        return self.json_path_query(self, json_path)

    def __and__(self, other: "QueryExpression") -> "QueryExpression":
        return type(self)('and', [self, self._convert_if_necessary(other)])

    def __rand__(self, other: "QueryExpression") -> "QueryExpression":
        return type(self)('and', [self._convert_if_necessary(other), self])

    def __or__(self, other: "QueryExpression") -> "QueryExpression":
        return type(self)('or', [self, self._convert_if_necessary(other)])

    def __ror__(self, other: "QueryExpression") -> "QueryExpression":
        return type(self)('and', [self._convert_if_necessary(other), self])

    def __invert__(self: "QueryExpression") -> "QueryExpression":
        return type(self)('not', [self])

    def __eq__(self, other):
        return type(self)('eq', [self, self._convert_if_necessary(other)])

    def __lt__(self, other) -> "QueryExpression":
        return type(self)('lt', [self, self._convert_if_necessary(other)])

    def __le__(self, other) -> "QueryExpression":
        return type(self)('le', [self, self._convert_if_necessary(other)])

    def __gt__(self, other) -> "QueryExpression":
        return type(self)('gt', [self, self._convert_if_necessary(other)])

    def __ge__(self, other) -> "QueryExpression":
        return type(self)('ge', [self, self._convert_if_necessary(other)])
