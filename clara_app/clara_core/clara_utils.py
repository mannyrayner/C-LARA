"""
This module contains utility functions for file operations, configuration, and other common tasks
"""

import os.path
import shutil
import json
import configparser
import re
import string
from pathlib import Path
from datetime import datetime
import uuid
import boto3
import botocore
import os
import zipfile
import tempfile
import chardet
import hashlib
import traceback
import requests
import subprocess

from PIL import Image

from asgiref.sync import sync_to_async

from .clara_classes import InternalCLARAError

_s3_storage = True if os.getenv('FILE_STORAGE_TYPE') == 'S3' else False


## Initialize Boto3 session if we are using S3
_s3_bucket_name = None
_s3_session = None
_s3_client = None
_s3_bucket = None

def initialise_s3():
    global _s3_bucket_name, _s3_session, _s3_client, _s3_bucket
    
    _s3_bucket_name = os.getenv('S3_BUCKET_NAME')
    
    _s3_session = boto3.Session(aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                                region_name=os.getenv('AWS_REGION'))

    _s3_client = _s3_session.client('s3')

    _s3_bucket = _s3_session.resource('s3').Bucket(_s3_bucket_name)

if _s3_storage:
    initialise_s3()

def s3_is_initialised():
    return True if _s3_session else False

def fail_if_no_s3_bucket():
    if not _s3_bucket_name:
        raise InternalCLARAError( message='FILE_STORAGE_TYPE is set to S3, but no value for S3_BUCKET_NAME' )

## Adjust file name to the relevant environment

## Expand the environment var and get an absolute path name if we are using local files
def absolute_local_file_name(pathname):
    if isinstance(pathname, ( Path )):
        pathname = str(pathname)
        
    pathname = os.path.abspath(os.path.expandvars(pathname))
        
    ## Replace backslashes with forward slashes
    return pathname.replace('\\', '/')

## Strip off any initial "$CLARA", "$CLARA/",  "$CLARA\" etc if we are using S3 
def s3_file_name(pathname):
    if isinstance(pathname, ( Path )):
        pathname = str(pathname)
        
    pathname = replace_local_path_prefixes_for_s3(pathname)
        
    ## Replace backslashes with forward slashes
    return pathname.replace('\\', '/')

def absolute_file_name(pathname):
    if isinstance(pathname, ( Path )):
        pathname = str(pathname)

    ## Strip off any initial "$CLARA", "$CLARA/", "$CLARA\" etc if we are using S3 
    if _s3_storage:
        pathname = replace_local_path_prefixes_for_s3(pathname)
    ## Expand the environment var and get an absolute path name if we are using local files
    else:
        pathname = os.path.abspath(os.path.expandvars(pathname))
        
    ## Replace backslashes with forward slashes
    return pathname.replace('\\', '/')

def replace_local_path_prefixes_for_s3(pathname):
    # Handle CLARA environment variable
    if pathname.startswith('$CLARA/'):
        pathname = pathname.replace('$CLARA/', '', 1)
    elif pathname.startswith('$CLARA\\'):
        pathname = pathname.replace('$CLARA\\', '', 1)
    elif pathname.startswith('$CLARA'):
        pathname = pathname.replace('$CLARA', '', 1)
    
    # Handle Windows drive letters with both forward and backslashes
    if re.match(r"^[A-Za-z]:[\\/]", pathname):
        pathname = pathname[3:]
    
    # Handle root directory
    if pathname.startswith('/'):
        pathname = pathname[1:]
    
    return pathname

def generate_s3_presigned_url(file_path, expiration=3600):
    """
    Generate a presigned URL for an S3 object.

    Parameters:
        file_path (str): The path to the file in the S3 bucket.
        expiration (int): Time in seconds for the presigned URL to remain valid.

    Returns:
        str: Presigned URL, or None if an error occurred.
    """
    if not s3_is_initialised():
        print(f'--- S3 storage is not initialised: unable to create presigned URL')
        return None

    try:
        response = _s3_client.generate_presigned_url('get_object',
                                                     Params={'Bucket': _s3_bucket_name,
                                                             'Key': file_path},
                                                     ExpiresIn=expiration)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return response

def make_directory(pathname, parents=False, exist_ok=False):
    if _s3_storage:
        # S3 doesn't actually require you to "make" directories because of its flat structure
        pass
    else:
        abspathname = Path(absolute_file_name(pathname))

        abspathname.mkdir(parents=parents, exist_ok=exist_ok)

def make_local_directory(pathname, parents=False, exist_ok=False):
    abspathname = Path(absolute_local_file_name(pathname))
    
    abspathname.mkdir(parents=parents, exist_ok=exist_ok)

def remove_directory(pathname):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        for obj in _s3_bucket.objects.filter(Prefix=abspathname):
            _s3_bucket.delete_objects(
                Delete={'Objects': [{'Key': obj.key}]})
    else:
        shutil.rmtree(abspathname)

def remove_local_directory(pathname, callback=None):
    abspathname = absolute_file_name(pathname)

    try:
        shutil.rmtree(abspathname)
    except FileNotFoundError as e:
        error_message = f"Warning: directory not found when trying to remove: {abspathname}"
        post_task_update(callback, error_message)
    except Exception as e:
        error_message = f"Error when trying to remove directory: {abspathname} - {str(e)}\n{traceback.format_exc()}"
        post_task_update(callback, error_message)
        raise

def copy_file(pathname1, pathname2):
    abspathname1 = absolute_file_name(pathname1)
    abspathname2 = absolute_file_name(pathname2)

    if abspathname1 == abspathname2:
        return

    if _s3_storage:
        fail_if_no_s3_bucket()
        _s3_bucket.copy({'Bucket': _s3_bucket_name, 'Key': abspathname1}, abspathname2)
    else:
        shutil.copyfile(abspathname1, abspathname2)

# In this version, pathname1 is a local file.
# pathname2 will be another local file or an S3 file, depending on the value of _s3_storage
def copy_local_file(pathname1, pathname2):
    abspathname1 = absolute_local_file_name(pathname1)
    abspathname2 = absolute_file_name(pathname2)

    if abspathname1 == abspathname2:
        return

    if _s3_storage:
        fail_if_no_s3_bucket()
        with open(abspathname1, "rb") as data:
            _s3_client.put_object(Bucket=_s3_bucket_name, Key=abspathname2, Body=data)

    else:
        shutil.copyfile(abspathname1, abspathname2)

# In this version, pathname2 is a local file.
# pathname1 will be another local file or an S3 file, depending on the value of _s3_storage
def copy_to_local_file(pathname1, pathname2):
    abspathname1 = absolute_file_name(pathname1)
    abspathname2 = absolute_local_file_name(pathname2)

    if _s3_storage:
        fail_if_no_s3_bucket()
        os.makedirs(os.path.dirname(abspathname2), exist_ok=True)

        with open(abspathname2, "wb") as data:
            _s3_client.download_fileobj(_s3_bucket_name, abspathname1, data)

    else:
        shutil.copyfile(abspathname1, abspathname2)

def copy_directory(pathname1, pathname2):
    abspathname1 = absolute_file_name(pathname1)
    abspathname2 = absolute_file_name(pathname2)

    if _s3_storage:
        fail_if_no_s3_bucket()
        
        # Make sure the pathnames end with '/'
        if not abspathname1.endswith('/'):
            abspathname1 += '/'
        if not abspathname2.endswith('/'):
            abspathname2 += '/'
        
        # List all objects in the source "directory" and copy them to the destination "directory"
        for obj in _s3_bucket.objects.filter(Prefix=abspathname1):
            old_source = { 'Bucket': _s3_bucket_name, 'Key': obj.key }
            new_key = obj.key.replace(abspathname1, abspathname2, 1)
            _s3_bucket.copy(old_source, new_key)
    else:
        shutil.copytree(abspathname1, abspathname2)

def copy_directory_to_local_directory(pathname1, pathname2):
    if _s3_storage:
        fail_if_no_s3_bucket()

        copy_directory_from_s3(pathname1, local_pathname=pathname2)
    else:
        copy_local_directory_to_local_directory(pathname1, pathname2)

def copy_local_directory_to_local_directory(pathname1, pathname2):
    abspathname1 = absolute_local_file_name(pathname1)
    abspathname2 = absolute_local_file_name(pathname2)

    shutil.copytree(abspathname1, abspathname2)

# Make an S3 copy of a file if we're in S3 mode and need to transfer the file to another file system.
# If we're not in S3 mode, we don't need to do anything: we just use the file as it is.
def copy_local_file_to_s3_if_necessary(local_pathname, callback=None):
    if _s3_storage:
        copy_local_file_to_s3(local_pathname, callback=callback)

def compute_md5(file_path):
    """Compute the MD5 checksum of a file."""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

# Copy a local file to S3, even if we aren't currently in S3 mode.
def copy_local_file_to_s3(local_pathname, s3_pathname=None, callback=None):
    if not s3_is_initialised():
        initialise_s3()

    fail_if_no_s3_bucket()

    try:
        s3_pathname = s3_pathname if s3_pathname else local_pathname
        abs_local_pathname = absolute_local_file_name(local_pathname)
        abs_s3_pathname = s3_file_name(s3_pathname)

        # Compute the MD5 checksum of the local file before uploading
        local_md5 = compute_md5(abs_local_pathname)

        with open(abs_local_pathname, "rb") as data:
            response = _s3_client.put_object(Bucket=_s3_bucket_name, Key=abs_s3_pathname, Body=data)

        # Verify the MD5 checksum with the one returned by S3
        s3_md5 = response.get('ETag', '').replace('"', '')
        if local_md5 != s3_md5:
            post_task_update(callback, f'*** Checksum mismatch for {abs_local_pathname}. Local MD5: {local_md5}, S3 MD5: {s3_md5}')
            return

        post_task_update(callback, f'--- Copied local file {abs_local_pathname} to S3 file {abs_s3_pathname}, bucket = {_s3_bucket_name}')
    except Exception as e:
        post_task_update(callback, f'*** Error: something went wrong when trying to local file {abs_local_pathname} to S3 file {abs_s3_pathname}: {str(e)}')
        raise InternalCLARAError( message=f'*** Error: something went wrong when trying to local file {abs_local_pathname} to S3') 

# If we're in S3 mode, retrieve a file which probably came from another file system.
# If we're not in S3 mode, we don't need to do anything: we just use the file as it is.
def copy_s3_file_to_local_if_necessary(s3_pathname, callback=None):
    if _s3_storage:
        copy_s3_file_to_local(s3_pathname, callback=callback)

# Copy an S3 local file to local, even if we aren't currently in S3 mode.
def copy_s3_file_to_local(s3_pathname, local_pathname=None, callback=None):
    if not s3_is_initialised():
        initialise_s3()

    fail_if_no_s3_bucket()

    local_pathname = local_pathname if local_pathname else s3_pathname
    s3_pathname = s3_file_name(s3_pathname)
    local_pathname = absolute_local_file_name(local_pathname)

    with open(local_pathname, "wb") as data:
        _s3_client.download_fileobj(_s3_bucket_name, s3_pathname, data)

    # Compute the MD5 checksum of the downloaded file
    downloaded_md5 = compute_md5(local_pathname)

    # Fetch the MD5 checksum of the file in S3
    response = _s3_client.head_object(Bucket=_s3_bucket_name, Key=s3_pathname)
    s3_md5 = response.get('ETag', '').replace('"', '')

    # Verify the MD5 checksum with the one of the downloaded file
    if downloaded_md5 != s3_md5:
        post_task_update(callback, f'*** Checksum mismatch for {local_pathname}. Downloaded MD5: {downloaded_md5}, S3 MD5: {s3_md5}')
        return

    post_task_update(callback, f'--- Copied S3 file {s3_pathname}, bucket = {_s3_bucket_name} to local file {local_pathname}')

# This function will normally be run on a local machine to sync an S3 directory with a local one
def copy_directory_to_s3(local_pathname, s3_pathname=None):
    fail_if_no_s3_bucket()
    
    s3_pathname = s3_pathname if s3_pathname else local_pathname
    local_pathname = absolute_local_file_name(local_pathname)
    s3_pathname = s3_file_name(s3_pathname)

    if not os.path.isdir(local_pathname):
        raise ValueError(f"{local_pathname} is not a directory.")

    for dirpath, _, filenames in os.walk(local_pathname):
        for filename in filenames:
            local_file = os.path.join(dirpath, filename)
            s3_file = os.path.join(s3_pathname, os.path.relpath(local_file, local_pathname))
            s3_file = s3_file.replace("\\", "/")  # Ensure we use "/" for S3 keys

            with open(local_file, "rb") as data:
                _s3_client.put_object(Bucket=_s3_bucket_name, Key=s3_file, Body=data)

def copy_directory_from_s3(s3_pathname, local_pathname=None):
    initialise_s3()
    
    fail_if_no_s3_bucket()

    local_pathname = local_pathname if local_pathname else s3_pathname
    s3_pathname = s3_file_name(s3_pathname)
    local_pathname = absolute_local_file_name(local_pathname)
    print(f'--- Initialised, downloading "{s3_pathname}" to "{local_pathname}"')

    if not s3_pathname.endswith("/"):
        s3_pathname += "/"

    continuation_token = None
    while True:
        list_objects_v2_params = {
            'Bucket': _s3_bucket_name,
            'Prefix': s3_pathname
        }
        if continuation_token:
            list_objects_v2_params['ContinuationToken'] = continuation_token

        s3_objects = _s3_client.list_objects_v2(**list_objects_v2_params)

        if 'Contents' not in s3_objects:
            print(f"No objects found with prefix {s3_pathname}")
            break

        print(f'--- Found {len(s3_objects["Contents"])} files for Bucket={_s3_bucket_name}, Prefix={s3_pathname}')

        for s3_object in s3_objects['Contents']:
            s3_file = s3_object['Key']
            print(f'--- Copying {s3_file}')
            local_file = os.path.join(local_pathname, os.path.relpath(s3_file, s3_pathname))
            local_file = local_file.replace("/", os.path.sep)  # Ensure we use the correct OS path separator

            os.makedirs(os.path.dirname(local_file), exist_ok=True)

            copy_s3_file_to_local(s3_file, local_pathname=local_file)

        if not s3_objects.get('IsTruncated'):  # No more pages
            break

        continuation_token = s3_objects.get('NextContinuationToken')


def file_exists(pathname):
    abspathname = absolute_file_name(pathname)
    
    if _s3_storage:
        fail_if_no_s3_bucket()
        try:
            _s3_client.head_object(Bucket=_s3_bucket_name, Key=abspathname)
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                # something else has gone wrong that we weren't expecting
                raise InternalCLARAError( message=f'Error in S3 when trying to access {abspathname}' )
    else:
        return os.path.isfile(abspathname)

def local_file_exists(pathname):
    abspathname = absolute_local_file_name(pathname)
    
    return os.path.isfile(abspathname)

def s3_file_exists(pathname):
    abspathname = s3_file_name(pathname)
    
    fail_if_no_s3_bucket()
    try:
        _s3_client.head_object(Bucket=_s3_bucket_name, Key=abspathname)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            # something else has gone wrong that we weren't expecting
            raise InternalCLARAError( message=f'Error in S3 when trying to access {abspathname}' )

def local_directory_exists(pathname):
    abspathname = absolute_local_file_name(pathname)

    return os.path.isdir(abspathname)
        
def directory_exists(pathname):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        # Append '/' to pathname to treat it as a directory
        if not abspathname.endswith('/'):
            abspathname += '/'
        # If the bucket contains any objects with the given prefix, we consider the directory to exist
        result = _s3_client.list_objects_v2(Bucket=_s3_bucket_name, Prefix=abspathname, MaxKeys=1)
        return 'Contents' in result
    else:
        return os.path.isdir(abspathname)

def list_files_in_directory(pathname):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        # Append '/' to pathname to treat it as a directory
        if not abspathname.endswith('/'):
            abspathname += '/'
        # Retrieve all objects with the given prefix
        result = _s3_client.list_objects_v2(Bucket=_s3_bucket_name, Prefix=abspathname)
        # If the bucket contains any objects with the given prefix, return their keys
        if 'Contents' in result:
            # Strip the prefix from each object key and return the list of keys
            return [item['Key'][len(abspathname):] for item in result['Contents']]
        else:
            return []
    else:
        return os.listdir(abspathname)

def remove_file(pathname):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        _s3_client.delete_object(Bucket=_s3_bucket_name, Key=abspathname)
    else:
        os.remove(abspathname)

def remove_local_file(pathname, callback=None):
    abspathname = absolute_local_file_name(pathname)

    try:
        os.remove(abspathname)
    except FileNotFoundError as e:
        error_message = f"Warning: file not found when trying to remove: {abspathname}"
        post_task_update(callback, error_message)
    except Exception as e:
        error_message = f"Error when trying to remove file: {abspathname} - {str(e)}\n{traceback.format_exc()}"
        post_task_update(callback, error_message)
        raise


def rename_file(pathname1, pathname2):
    abspathname1 = absolute_file_name(pathname1)
    abspathname2 = absolute_file_name(pathname2)

    if _s3_storage:
        fail_if_no_s3_bucket()
        # In S3, renaming is effectively copying and then deleting the original file
        _s3_client.copy({'Bucket': _s3_bucket_name, 'Key': abspathname1}, _s3_bucket_name, abspathname2)
        _s3_client.delete_object(Bucket=_s3_bucket_name, Key=abspathname1)
    else:
        Path(abspathname1).rename(Path(abspathname2))

def read_json_file(pathname):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        obj = _s3_bucket.Object(abspathname).get()
        return json.load(obj['Body'])
    else:
        with open(abspathname, encoding='utf-8') as f:
            return json.load(f)

def read_local_json_file(pathname):
    abspathname = absolute_local_file_name(pathname)

    with open(abspathname, encoding='utf-8') as f:
        return json.load(f)

def read_json_local_file(pathname):
    return read_local_json_file(pathname)

def write_json_to_file(data, pathname):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        _s3_client.put_object(Bucket=_s3_bucket_name, Key=abspathname, Body=json.dumps(data, indent=4))
    else:
        with open(abspathname, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4) 

def write_json_to_local_file(data, pathname):
    abspathname = absolute_local_file_name(pathname)

    with open(abspathname, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4) 

def write_json_to_file_plain_utf8(data, pathname):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        _s3_client.put_object(Bucket=_s3_bucket_name, Key=abspathname, Body=json.dumps(data, indent=4, ensure_ascii=False))
    else:
        with open(abspathname, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False) 

def read_txt_file(pathname: str):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        obj = _s3_client.get_object(Bucket=_s3_bucket_name, Key=abspathname)
        return obj['Body'].read().decode('utf-8')
    else:
        with open(abspathname, 'r', encoding='utf-8') as f:
            return f.read()

def read_local_txt_file(pathname: str):
    abspathname = absolute_local_file_name(pathname)

    with open(abspathname, 'r', encoding='utf-8') as f:
        return f.read()

def check_if_file_can_be_read(pathname: str) -> bool:
    try:
        data = robust_read_local_txt_file(pathname)
        print(f"--- File {pathname} could be read")
        return True
    except Exception as e:
        print(f"*** File {pathname} could not be read")
        print(f"Exception: {str(e)}\n{traceback.format_exc()}")
        return False
           
# Version that can be used when we're uncertain about the encoding
def robust_read_local_txt_file(pathname: str) -> str:
    abspathname = absolute_local_file_name(pathname)
    
    # Detect the file's encoding
    with open(abspathname, 'rb') as f:
        rawdata = f.read()
        result = chardet.detect(rawdata)
        encoding = result['encoding']

    # Print the detected encoding for debugging
    print(f"Detected encoding: {encoding}")

    # Handle BOM for UTF encodings
    if encoding == "UTF-16LE" or encoding == "UTF-16BE":
        mode = 'r'
        encoding = 'utf-16'
    elif encoding == "UTF-32LE" or encoding == "UTF-32BE":
        mode = 'r'
        encoding = 'utf-32'
    else:
        mode = 'r'

    # Read the file using the detected encoding
    with open(abspathname, mode, encoding=encoding) as f:
        return f.read()


def write_txt_file(data, pathname: str):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        _s3_client.put_object(Bucket=_s3_bucket_name, Key=abspathname, Body=data)
    else:
        with open(abspathname, 'w', encoding='utf-8') as f:
            f.write(data)
            
def write_local_txt_file(data, pathname: str):
    abspathname = absolute_local_file_name(pathname)

    with open(abspathname, 'w', encoding='utf-8') as f:
        f.write(data)

def read_json_or_txt_file(file_path: str):
    extension = extension_for_file_path(file_path)
    abs_file_path = absolute_file_name(file_path)

    if extension == 'json':
        data = read_json_file(abs_file_path)
    elif extension == 'txt':
        data = read_txt_file(abs_file_path)
    else:
        raise ValueError(f'Unsupported file type {extension} for {file_path}')
    
    return data

def write_json_or_txt_file(data, file_path: str):
    extension = extension_for_file_path(file_path)
    abs_file_path = absolute_file_name(file_path)

    if extension == 'json':
        write_json_to_file_plain_utf8(data, file_path)
    elif extension == 'txt':
        write_txt_file(data, file_path)
    else:
        raise ValueError(f'Unsupported file type {extension} for {file_path}')

def get_immediate_subdirectories_in_local_directory(a_dir):
    abs_dir = absolute_local_file_name(a_dir)
    return [name for name in os.listdir(abs_dir)
            if os.path.isdir(os.path.join(abs_dir, name))]

def get_files_in_local_directory(a_dir):
    abs_dir = absolute_local_file_name(a_dir)
    return [name for name in os.listdir(abs_dir)
            if os.path.isfile(os.path.join(abs_dir, name))]

def download_file_from_url(url, file_path):
    abs_file_path = absolute_local_file_name(file_path)
    
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code == 200:
        # Save the content to a local file
        with open(abs_file_path, "wb") as f:
            f.write(response.content)
        print(f"File downloaded successfully to {abs_file_path}.")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")

def get_image_dimensions(image_path, callback=None):
    """Get the dimensions of an image file.
    
    Args:
        image_path (str): The path to the image file.
    
    Returns:
        tuple: The dimensions of the image as (width, height).
    """
    try:
        abspathname = absolute_file_name(image_path)
        
        if _s3_storage:
            obj = _s3_client.get_object(Bucket=_s3_bucket_name, Key=abspathname)
            image = Image.open(obj['Body'])
        else:
            image = Image.open(abspathname)
    
        return image.size
    except Exception as e:
        post_task_update(callback, f"An error occurred while processing the image at path: {image_path}")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        return ( None, None )

def extension_for_file_path(file_path: str):
    if isinstance(file_path, Path):
        file_path = str(file_path)
    return file_path.split('.')[-1]

def remove_extension_from_file_path(file_path: str):
    if isinstance(file_path, Path):
        file_path = str(file_path)
    return '.'.join(file_path.split('.')[:-1])

def basename(pathname):
    return os.path.basename(pathname)

def pathname_parts(pathname):
    # On a UNIX machine, it seems that Path.parts doesn't work on a Windows pathname,
    # but on a Windows machine it works on a UNIX pathname. So convert to UNIX form
    pathname1 = pathname.replace('\\', '/')
    return Path(pathname1).parts

def get_file_time(pathname, time_format='float'):
    abspathname = absolute_file_name(pathname)

    if _s3_storage:
        fail_if_no_s3_bucket()
        obj = _s3_client.head_object(Bucket=_s3_bucket_name, Key=abspathname)
        float_value = obj['LastModified'].timestamp()
    else:
        float_value = Path(abspathname).stat().st_mtime

    if time_format == 'timestamp':
        return datetime.fromtimestamp(float_value)
    else:
        return float_value
      
def make_tmp_file(prefix, extension):
    return f"$CLARA/tmp/{prefix}_{uuid.uuid4()}.{extension}"

def print_and_flush(Object):
    try:
        print(Object, flush=True)
    except:
        report_encoding_error(Object)

def report_encoding_error(Str):
    try:
        import unidecode
        Str1 = unidecode.unidecode(str(Str))
        print(f'{Str1} [some characters changed, encoding problems]')
    except:
        print(_encodingError)
        
def os_environ_or_none(environment_variable):
    try:
        return os.environ[environment_variable]
    except:
        return None

## Merge two dictionaries
def merge_dicts(X, Y):
    return { **X, **Y } 

##def get_config():
##    file = '$CLARA/clara_app/clara_core/config.ini'
##    if not local_file_exists(file):
##        raise InternalCLARAError( message=f'Unable to find config file {file}')
##    config = configparser.ConfigParser()
##    config.read(absolute_local_file_name(file))
##    return config

def get_config():
    file = '$CLARA/clara_app/clara_core/config.ini'
    absfile = absolute_local_file_name(file)
    if not local_file_exists(absfile):
        raise InternalCLARAError(f'Unable to find config file {absfile}')
    config = configparser.ConfigParser()
    config.read(absfile)
    return config

def output_dir_for_project_id(id, phonetic_or_normal):
    config = get_config()
    if phonetic_or_normal == 'normal':
        return str( Path(absolute_file_name(config.get('renderer', 'output_dir'))) / str(id) )
    else:
        return str( Path(absolute_file_name(config.get('renderer', 'output_dir_phonetic'))) / str(id) )

def image_dir_for_project_id(id):
    config = get_config()
    return str( Path(absolute_file_name(config.get('image_repository', 'base_dir'))) / str(id) )

def is_rtl_language(language):
    rtl_languages = ['arabic', 'hebrew', 'farsi', 'urdu', 'yemeni']
    return language in rtl_languages

def is_chinese_language(language):
    chinese_languages = [ 'chinese', 'mandarin', 'cantonese', 'taiwanese' ]
    return language in chinese_languages

def make_line_breaks_canonical_linesep(text):
    # Normalize all line breaks to '\n' first
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Then replace '\n' with the system's line separator
    return text.replace('\n', os.linesep)

def make_line_breaks_canonical_n(text):
    # Normalize all line breaks to '\n'
    return text.replace('\r\n', '\n').replace('\r', '\n')

def format_timestamp(timestamp_string):
    try:
        # convert the timestamp string into a datetime object
        dt = datetime.strptime(timestamp_string, "%Y%m%d%H%M%S")

        # format the datetime object into a string
        return dt.strftime("%B %d %Y %H:%M:%S")
    except:
        return timestamp_string
    
def replace_punctuation_with_underscores(s):
    return re.sub(f"[{re.escape(string.punctuation)}]+", "_", s)

## Zip up a directory
def make_zipfile(directory, zipfile, callback=None):
    absdirectory = absolute_local_file_name(directory)
    abszipfile = absolute_local_file_name(zipfile)
    # shutil.make_archive adds a .zip extension even if you already have one
    abszipfile_without_extension = remove_extension_from_file_path(abszipfile)
    try:
        shutil.make_archive(abszipfile_without_extension, 'zip', absdirectory)
        print(f'--- Zipped up {directory} as {zipfile}')
        return True
    except Exception as e:
        post_task_update(callback, f'--- Error when trying to zip {directory} to {zipfile}: {str(e)}')
        raise InternalCLARAError( message=f'*** Error: something went wrong when trying to unzip {pathname} to {dir}')

## Extract a zipfile to a directory
def unzip_file(pathname, dir, callback=None):
    abspathname = absolute_local_file_name(pathname)
    absdirname = absolute_local_file_name(dir)
    if not local_file_exists(abspathname):
        message = f'Unable to find file {abspathname}'
        raise InternalCLARAError( message=message )
    try:
        zip_ref = zipfile.ZipFile(abspathname, 'r')  
        zip_ref.extractall(absdirname)
        zip_ref.close()
        #post_task_update(callback, f'--- Unzipped {pathname} to {dir}')
        return True
    except Exception as e:
        post_task_update(callback, f'--- Error when trying to unzip {pathname} to {dir}: {str(e)}')
        raise InternalCLARAError( message=f'*** Error: something went wrong when trying to unzip {pathname} to {dir}') 

# This assumes that 'callback' is a callback function taking one arg
# If it is non-null, call it on the message.
# Also print the message.
#
# The intention is that calling the callback posts the message,
# suitably associating it with the report ID, which should be part of the callback

# Wrap this version in sync_to_async so that we can post updates in asynchronous contexts.
# We need it in particular in clara_chatgpt4
@sync_to_async
def post_task_update_async(callback, message):
    post_task_update(callback, message)

##def post_task_update(callback, message):
##    if callback and isinstance(callback, ( list, tuple )) and len(callback) == 2:
##        callback_function, report_id = callback
##        callback_function(report_id, message)
##        print(f"Posted task update: '{message}'")
##    elif callback:
##        print(f"Error: bad callback: {callback}. Must be a two element list.")
##    else:
##        print(f"Could not post task update '{message}'. Callback = {callback}")

def post_task_update(callback, message):
    if callback and isinstance(callback, ( list, tuple )) and len(callback) == 4:
        callback_function, report_id, user_id, task_type = callback
        callback_function(report_id, user_id, task_type, message)
        #print(f"Posted task update: '{message}'")
        print(f"Posted task update: '{message}' (user_id={user_id}, task_type={task_type})")
    elif callback:
        print(f"Error: bad callback: {callback}. Must be a four element list.")
    else:
        print(f"{message} [callback = {callback}]")
    
def canonical_word_for_audio(text):
    return text.lower()

def canonical_text_for_audio(text, phonetic=False):
    if phonetic:
        return canonical_word_for_audio(text.strip())
    else:
        # Remove HTML markup
        text = re.sub(r'<[^>]*>', '', text)

        # Consolidate sequences of whitespaces to a single space
        text = re.sub(r'\s+', ' ', text)

        # Trim leading and trailing spaces
        text = text.strip()

        return text

def remove_blank_lines(text):
    lines = text.split('\n')
    return '\n'.join([ line for line in lines if len(line.strip()) != 0 ])

def remove_duplicates_from_list_of_hashable_items(items):
    return list(dict.fromkeys(items))

## Slower version for lists with non-hashable elements
def remove_duplicates_general(items):
    ( out, dictionary ) = ( [], {} )
    for X in items:
        string = str(X)
        if not string in dictionary:
            out += [ X ]
            dictionary[string] = True
    return out

def make_mp3_version_of_audio_file_if_necessary(source_file):
    if extension_for_file_path(source_file) == 'mp3':
        return source_file
    else:
        abssource_file = absolute_local_file_name(source_file)
        # Create a temporary file with a .mp3 suffix
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_file_path = temp_file.name
        temp_file.close()  # Close the file to allow ffmpeg to write to it

        try:
            # Run ffmpeg to convert the source file to MP3
            result = subprocess.run(["ffmpeg", "-i", abssource_file, temp_file_path], capture_output=True, text=True)

            if result.returncode != 0:
                # If ffmpeg failed, delete the temporary file and raise an error
                remove_local_file(temp_file_path)
                raise InternalCLARAError(message=f'*** Error in ffmpeg conversion: {result.stderr}')

            if not local_file_exists(temp_file_path):
                raise InternalCLARAError(message=f'*** Error: MP3 file not created for {source_file}')

            return temp_file_path
        except Exception as e:
            if local_file_exists(temp_file_path):
                remove_local_file(temp_file_path)
            raise InternalCLARAError(message=f'*** Error: Exception occurred during conversion of {source_file} to mp3: {str(e)}')
