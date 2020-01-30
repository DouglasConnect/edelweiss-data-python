#!/usr/bin/env python
# coding: utf-8

# # EdelweissData Python client API demonstration

# ## Setup

# In[1]:


from edelweiss_data import API, QueryExpression as Q
import pandas
import requests


# In[2]:


from IPython.core.display import HTML

edelweiss_ui_url = 'https://ui.develop.edelweiss.douglasconnect.com'

def display_link_to_published_dataset(id, version):
    dataset_url = '{}/dataexplorer?dataset={}:{}'.format(edelweiss_ui_url, id, version)
    return HTML('<a href="{}">View the dataset {} in the browser</a>'.format(dataset_url, id))


# #### Set up connection

# In[3]:


edelweiss_api_url = 'https://api.develop.edelweiss.douglasconnect.com'
#edelweiss_api_url = 'http://localhost:8000'


# In[4]:


api = API(edelweiss_api_url)


# #### Authenticate yourself to edelweiss.
# 
# The default authentication uses Auth0Jwt. You will be asked to visit a url in a web browser to confirm who you are. You can skip this step if you want to view only publicly visible datasets.
# 
# You can also use development mode, which skips the proper authentication.

# In[5]:


api.authenticate()
#api.authenticate(development=True)


# ### Get a dataframe of all published datasets

# In[6]:


datasets = api.get_published_datasets()
datasets


# In[7]:


first = datasets.iloc[0].dataset


# In[8]:


display_link_to_published_dataset(first.id, first.version)


# ### Create a new dataset from file (high level operation)
# 
# Here everything is done automatically – you pass in an open file, a name and an optional arbitrary metadata dict and the dataset is created, uploaded and published. The returned value is an instance of the `PublishedDataset` class (see below for how to get a `pandas.DataFrame` from the dataset).

# In[9]:


with open ('../../tests/Serialization/data/small1.csv') as f:
    dataset = api.create_published_dataset_from_csv_file("python test", f, {"metadata-dummy-string": "string value", "metadata-dummy-number": 42.0})
dataset                                                                       


# ### Get data from a published dataset

# In[10]:


dataframe = dataset.get_data()
dataframe


# In[11]:


aggregations = dataset.get_data_aggregations()
aggregations[aggregations != len(dataframe)]


# ### Delete a dataset and all its versions

# In[12]:


dataset2 = api.get_published_dataset(dataset.id, version='latest')
dataset2


# In[13]:


dataset2.delete_all_versions()


# ### Create new dataset from file – the manual way
# 
# Here we have to: 
# * create a new in-progress dataset
# * Upload the data
# * Infer a schema (or we could alternatively upload one)
# * Optionally upload metadata (a python dict object that will be serialized as json)
# * Finally publish the dataset
# 

# In[14]:


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


# In[15]:


dataset1.metadata

