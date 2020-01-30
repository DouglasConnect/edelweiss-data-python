This python client library allows easy access to [Edelweiss Data](https://www.saferworldbydesign.com/edelweissdata) servers.

# Table of Contents

- [Overview](#overview)
- [Getting started](#getting-started)
  - [Requirements](#requirements)
  - [Installation](#installation)
- [Common use cases](#common-use-cases)
  - [Authentication](#authentication)
  - [Create a new dataset](#create-a-new-dataset)
  - [Search for datasets](#search-for-datasets)
  - [Filter and retrieve data](#filter-and-retrieve-data)
- [API reference](#api-reference)


## Overview

The core concept of Edelweiss Data is that of a **Dataset**. A Dataset is a single table of data (usually originating from a csv file) and carries the following additional pieces of information:
* a **schema** describing the structure of the tabular data (data types, explanatory text for each column etc)
* a human readable **description text** (markdown formatted - like the readme of a repository on github)
* a **metadata json** structure (of arbitrary complexity - this can be used to store things like author information, instrument settings used to generate the data, ...).

Datasets are **versioned** through a processes called publishing. Once a version of a dataset is published, it is "frozen" and becomes immutable. Any change to it has to be done by creating a new version. Users of Edelweiss Data will always see the version history of a dataset and be able to ask for the latest version or specific earlier version.

Datasets can be public or **access restricted**. Public datasets can be accessed without any access restrictions. To access restricted datasets or to upload/edit your own dataset OpenIDConnect/OAuth is used - in the python client this process is done by calling the authenticate method on the Api instance that triggers a web based login at the end of which a token is confirmed.

When retrieving the tabular data of a dataset, the data can be filtered and ordered and only specific columns requested - this makes request for subsets of data much faster than if all filtering happened only on the client. Conditions for filtering and ordering are created by constructing QueryExpression instances using classmethods on the QueryExpression class to create specific Expressions. You can access the data either in it's raw form (as json data) or, more convieniently, as a Pandas Dataframe.

Just like the tabular data of one particular dataset can be retrieved as a Pandas DataFrame, you can also query for datasets using the same filtering and ordering capabilities - i.e. you can retrieve a DataFrame where each row represents a Dataset with it's name, description and optionally metadata and schema (not including the data though).

When you are searching for Datasets, a lot of the interesting information that you may want to filter by is hidden in the metadata (e.g. maybe most of your datasets have a metadata field "Species" at the top level of the metadata json that indicates from what kind of animal cells the data in this dataset originate from). To make such filterings easy, our Datasets query function take an optional list of "column mappings" that allow you to specify a JsonPath expression to extract a field from the metadata and include it with a given name in the resulting DataFrame. In the Species example, you could pass the list of column mappings [("Species from Metadata", "$.Species")] and the resulting DataFrame would contain an additional column "Speicies from Metadata" and for every row the result of evaluating the JsonPath $.Species would be included in this column and you could filter on it using conditions to e.g. only retrieve Datasets where the Species is set to "Mouse".

Edelweiss Data servers provide a rich User Interface as well that let's you visually browse and filter datasets and the data (and associated information) of each dataset. This UI is built to integate nicely with the python client. The DataExplorer that is used to explore a dataset has a button in the upper right corner to generate the python code to get the exact same filtering and ordering you see in the UI into a Pandas DataFrame using the Edelweiss Data library for your convinience.

## Installation

```bash
pip install edelweiss_data
```

## Usage

### Initialize the connection

```python
from edelweiss_data import API, QueryExpression as Q

# Set this to the url of the Edelweiss Data server you want to interact with
edelweiss_api_url = 'https://api.develop.edelweiss.douglasconnect.com'

api = API(edelweiss_api_url)
api.authenticate()

```

### Retrieve datasets that match a filter
```python
datasets_filter = Q.search_anywhere("LTKB")
datasets = api.get_published_datasets(condition=datasets_filter)
```

### Access schema and metadata of a dataset
```python
# assumes you have selected one dataset form a query like above into a variable dataset

column_count = len(dataset.schema.columns)
print("".format())
```
