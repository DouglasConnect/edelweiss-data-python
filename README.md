This python client library allows easy access to [Edelweiss Data](https://www.saferworldbydesign.com/edelweissdata) servers.

# Table of Contents

- [Overview](#overview)
- [Getting started](#getting-started)
  - [Requirements](#requirements)
  - [Installation](#installation)
- [Common use cases](#common-use-cases)
  - [Initialization](#initialization)
  - [Authentication](#authentication)
  - [Create a new dataset](#create-a-new-dataset)
  - [Search for datasets](#search-for-datasets)
  - [Filter and retrieve data](#filter-and-retrieve-data)
  - [Delete a new dataset](#delete-a-dataset)
- [API reference](#api-reference)

# Overview

The core concept of Edelweiss Data is that of a **Dataset**. A Dataset is a single table of data (usually originating from a csv file) and carries the following additional pieces of information:
* a **schema** describing the structure of the tabular data (data types, explanatory text for each column etc)
* a human readable **description text** (markdown formatted - like the readme of a repository on github)
* a **metadata json** structure (of arbitrary complexity - this can be used to store things like author information, instrument settings used to generate the data, ...).

Datasets are **versioned** through a processes called publishing. Once a version of a dataset is published, it is "frozen" and becomes immutable. Any change to it has to be done by creating a new version. Users of Edelweiss Data will always see the version history of a dataset and be able to ask for the latest version or specific earlier version.

Datasets can be public or **access restricted**. Public datasets can be accessed without any access restrictions. To access restricted datasets or to upload/edit your own dataset OpenIDConnect/OAuth is used - in the python client this process is done by calling the authenticate method on the Api instance that triggers a web based login at the end of which a token is confirmed.

When retrieving the tabular data of a dataset, the data can be **filtered and ordered** and only specific columns requested - this makes request for subsets of data much faster than if all filtering happened only on the client. Conditions for filtering and ordering are created by constructing QueryExpression instances using classmethods on the QueryExpression class to create specific Expressions. You can access the data either in it's raw form (as json data) or, more conveniently, as a Pandas Dataframe.

Just like the tabular data of one particular dataset can be retrieved as a **Pandas DataFrame**, you can also query for datasets using the same filtering and ordering capabilities - i.e. you can retrieve a DataFrame where each row represents a Dataset with it's name, description and optionally metadata and schema (not including the data though).

When you are searching for Datasets, a lot of the interesting information that you may want to filter by is hidden in the **metadata** (e.g. maybe most of your datasets have a metadata field "Species" at the top level of the metadata json that indicates from what kind of animal cells the data in this dataset originate from). To make such filtering easy, our Datasets query function take an optional list of "column mappings" that allow you to specify a **JsonPath expression** to extract a field from the metadata and include it with a given name in the resulting DataFrame. In the Species example, you could pass the list of column mappings [("Species from Metadata", "$.Species")] and the resulting DataFrame would contain an additional column "Species from Metadata" and for every row the result of evaluating the JsonPath $.Species would be included in this column and you could filter on it using conditions to e.g. only retrieve Datasets where the Species is set to "Mouse".

Edelweiss Data servers provide a rich **User Interface** as well that let's you visually browse and filter datasets and the data (and associated information) of each dataset. This UI is built to integrate nicely with the python client. The DataExplorer that is used to explore a dataset has a button in the upper right corner to generate the python code to get the exact same filtering and ordering you see in the UI into a Pandas DataFrame using the Edelweiss Data library for your convenience.

# Getting started

## Requirements

Python 3.6+

## Installation

```bash
pip install edelweiss_data
```

# Common use cases

## Initialization

You interact with the Edelweiss Data API mainly via the API class of the edelweiss_data python library. Import it, point it at the Edelweiss Data instance you want to interact with and instantiate it like this:

```python
from edelweiss_data import API, QueryExpression as Q

# Set this to the url of the Edelweiss Data server you want to interact with
edelweiss_api_url = 'https://api.develop.edelweiss.douglasconnect.com'

api = API(edelweiss_api_url)

```

## Authentication

Some operations in Edelweiss Data are accessible without authentication (e.g. retrieving public datasets). For others (e.g. to create datasets), you need to be authenticated. Authentication is done with the authenticate call. Be aware that this call is currently built for interactive use like in a Jupyter environment - it will block execution for a up to a few minutes while it waits for you to log in to your account and confirm the access to the API on your behalf. Once accepted the python client will store the authentication token so that you will not have to enter it again for a few days (the token is stored in your home directory in the .edelweiss directory).

```python
api.authenticate()
```

## Create a new dataset

Creating and publishing a new dataset form a csv file can be done in one quick operation like so:

```python
metadata = {"metadata-dummy-string": "string value", "metadata-dummy-number": 42.0}
with open ('FILENAME') as f:
    dataset = api.create_published_dataset_from_csv_file("DATASETNAME", f, metadata)
```

This creates a new dataset form the file FILENAME with the name DATASETNAME. A trivial example metadata is used here as well.

When creating and publishing datasets like this you don't have a lot of control over details of the schema or to set a more elaborate dataset description. If you need more control, you can create a dataset like so:

```python
datafile = '../../tests/Serialization/data/small1.csv'
name = 'My dataset'
schemafile = None # if none, schema will be inferred below
metadata = None # dict object that will be serialized to json or None
metadatafile = None # path to the metadata file or None
description = "This is a *markdown* description that can use [hyperlinks](https://edelweissconnect.com)"

dataset1 = api.create_in_progress_dataset(name)
print('DATASET:', dataset1)
try:
    with open(datafile) as f:
        dataset1.upload_data(f)
    if schemafile is not None:
        print('uploading schema from file ...')
        with open(schemafile) as f:
            dataset1.upload_schema_file(f)
    else:
        print('inferring schema from file ...')
        dataset1.infer_schema()
    if metadata is not None:
        print('uploading metadata ...')
        dataset1.upload_metadata(metadata)
    elif metadatafile is not None:
        print('uploading metadata from file ...')
        with open(metadatafile) as f:
            dataset1.upload_metadata_file(f)

    dataset1.set_description(description)

    published_dataset = dataset1.publish('My first commit')
    print('DATASET published:',published_dataset)
except requests.HTTPError as err:
    print('not published: ', err.response.text)
```

## Filter and retrieve data

The tabular data of an individual dataset can be retrieved into a pandas dataframe easily like this:

```python
dataframe = dataset.get_data()
```

You can also filter and order data with QueryExpressions, often aliased to Q in the import statement. In the following example we assume the data to have a column "Species" which we want to filter to the value "Mouse" with fuzzy text matching and "Chemical name" which we want to order by ascending:

```python
dataframe = dataset.get_data(condition=Q.fuzzy_search(Q.column("Species"), "Mouse"), order_by=[Q.column("Chemical name")])
```

## Search for datasets

To just retrieve a pandas dataframe with all published datasets that you are allowed to see use get_published_datasets(). This will return a pandas dataframe with three columns: the dataset id, the version, and the dataset class instance. This class instance can be used to retrieve e.g. the name property of the dataset or it can be used to retrieve the data for this dataset or similar operations.

```python
datasets = api.get_published_datasets()
dataset = datasets.iloc[0].dataset
print("Found {} datasets. The name of the first is: ".format(len(datasets), dataset.name))
```

Just like above with data you can use QueryExpressions to filter to only find datasets matching certain predicates. Below we filter on datasets that have the string "LTKB" somewhere in them (name etc)

```python
datasets_filter = Q.search_anywhere("LTKB")
datasets = api.get_published_datasets(condition=datasets_filter)
```

Since very often the most interesting filter and sort critieria will be in the metadata (which is a Json of arbitrary structure), the Api gives you a way to add additional columns by extracting pieces from the metadata json with JsonPath expressions. Below we attempt to treat the metadata json of each dataset as an object with a key "Species" and if it is present we extract it and map it into the "Species from metadata json" column:

```python
columns = [("Species from metadata json", "$.Species")]
datasets = api.get_published_datasets(columns=columns)
```

The result of such a query will always be a column containing lists of results as the jsonpath query could return not just a single primitive value or null or an object but also json arrays.

## Delete a dataset

To delete a dataset and all versions call delete_all_versions:

```python
dataset.delete_all_versions()
```

# API reference

TODO
