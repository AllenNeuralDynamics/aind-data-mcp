"""NWB file access tools."""

import re
from pathlib import Path
from urllib.parse import urlparse

import boto3
from hdmf_zarr import NWBZarrIO
from suffix_trees import STree

from .mcp_instance import mcp


@mcp.tool()
def identify_nwb_contents_in_code_ocean(subject_id, date):
    """
    Searches the /data directory in a code ocean repository for a folder
    and subfolder containing the subject_id and date,
    and loads the corresponding NWB file.

    Parameters:
    - subject_id (str): Subject identifier to search for in directory names
    - date (str): Date string (e.g. '2023-05-09') to search for in directory names

    Returns:
    - nwbfile: Loaded NWBFile object if found, else None
    """

    # Create pattern for matching
    pattern = rf".*{subject_id}.*{date}.*"
    base_path = Path("/data")

    # Find matching first-level directories
    first_matches = [
        d
        for d in base_path.iterdir()
        if d.is_dir() and re.search(pattern, d.name)
    ]

    if not first_matches:
        # print(f"Directory matching subject_id={subject_id} and date={date} not found in /data.")
        return None

    first_dir = first_matches[0]
    # print(f"Found first-level directory: {first_dir.name}")

    # Find matching second-level directories
    second_matches = [
        d
        for d in first_dir.iterdir()
        if d.is_dir() and re.search(pattern, d.name)
    ]

    if not second_matches:
        # print(f"No second-level directory matching subject_id={subject_id} and date={date} found.")
        return None

    nwb_path = second_matches[0]
    print(f"Found second-level directory: {nwb_path.name}")

    # Check if path exists and load NWB file
    try:
        with NWBZarrIO(str(nwb_path), "r") as io:
            nwbfile = io.read()
            # print('Loaded NWB file from:', nwb_path)
            return (
                nwbfile.all_children()
            )  # combination of files in data/asset/asset_nwb
    except Exception as e:
        # print(f'Error loading file from {nwb_path}: {e}')
        return None


@mcp.tool()
def identify_nwb_contents_with_s3_link(s3_link):
    """
    Identifies NWB folder in the given S3 link and opens it as a
    NWBZarrIO object.

    Parameters:
        s3_link (str): The S3 link to the folder or file.

    Returns:
        list: List of contents in NWB folder if found, otherwise None.
    """
    # Parse the S3 link
    parsed_url = urlparse(s3_link)
    bucket_name = parsed_url.netloc
    prefix = parsed_url.path.lstrip("/")

    # Initialize S3 client
    s3 = boto3.client("s3")

    try:
        # List objects in the given S3 path
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        if "Contents" in response:
            list_nwb_files = []
            for obj in response["Contents"]:
                directory_name = obj["Key"]
                if "nwb" in directory_name.lower():
                    list_nwb_files.append(directory_name)
        # Identifying common substring in all nwb files (ideally, nwb folder)
        s3_nwb_folder = STree.STree(list_nwb_files).lcs()
        s3_link_to_nwb = f"s3://{bucket_name}/{s3_nwb_folder}"
        # Opening s3 link to nwb folder as an nwb object
        with NWBZarrIO(str(s3_link_to_nwb), "r") as io:
            nwbfile = io.read()  # type pynwb.file.NWBFile
            file_contents = (
                nwbfile.all_children()
            )  # return nwbfile.allchildren() list contents as a list
            print("Loaded NWB file from:", s3_link_to_nwb)
        return file_contents
    except Exception as e:
        # print(f"Error accessing S3: {e}")
        return None

