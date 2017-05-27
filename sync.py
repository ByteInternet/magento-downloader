#!/usr/bin/env python3

import os
import requests
import json
import itertools
import hashlib
import urllib
from collections import defaultdict

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, **kwargs: x

MAGEID = os.environ['MAGEID']
TOKEN = os.environ['TOKEN']

"""
$ curl -k https://$MAGEID:$TOKEN@www.magentocommerce.com/products/downloads/info/help

Downloads Usage:
  [wget|curl -O] https://MAG_ID:TOKEN@www.magentocommerce.com/products/downloads/file/[FILENAME]

Info Usage:
  curl https://MAG_ID:TOKEN@www.magentocommerce.com/products/downloads/info/[OPTION]/[PARAMS]

Options:

  help          This help
  files         List of all available files for download
  versions      Versions list
  filter        Filtered list of all available files for download (see "Filter Options" for usage)
  json          The JSON feed of all available files

Filter Params:

  version       Shows files by version number. You can use wildcard.
                Example: /downloads/info/filter/version/1.9.2.1
                Example: /downloads/info/filter/version/1.9.*

  type          Shows files by file type:

                ce-full     - Community Edition - Full
                ee-full     - Enterprise Edition - Full
                ce-patch    - Community Edition - Patch
                ee-patch    - Enterprise Edition - Patch
                other       - Other

                Example: /downloads/info/filter/type/ce-full

"""

import requests_cache
requests_cache.install_cache()


def download_file(filename, path):
    url = 'https://www.magentocommerce.com/products/downloads/file/' + urllib.parse.quote(filename)
    print("Downloading {}".format(url))
    resp = requests.get(url, stream=True, auth=(MAGEID, TOKEN))

    if resp.status_code != 200:
        print("Status code {} for {}, aborting".format(resp.status_code, url))
        return False

    totalsize = int(resp.headers.get('content-length'))

    with open(path, 'wb') as fh:
        for data in tqdm(resp.iter_content(), total=totalsize, unit='B', unit_scale=True):
            fh.write(data)

    print("Saved {}".format(path))

def verify_md5sum(path, want_md5):

    if not os.path.exists(path):
        print("file does not exist: {}".format(path))
        return False

    if not want_md5:  # 2.0.7 doesn't have checksums, so don't check that if the file exists
        return True

    with open(path, 'rb') as fh:
        data = fh.read()

    real_md5 = hashlib.md5(data).hexdigest()
    same = real_md5 == want_md5
    if not same:
        print("file {} exists but has different checksum {}".format(path, real_md5))

    return same


def sync_everything(all_files):
    # print(json.dumps(blob, indent=2))
    for category, files in all_files.items():
        assert category in ('other', 'ee-full', 'ce-full', 'ee-patch', 'ce-patch'), \
            'unknown category: {}'.format(category)

        if not os.path.exists(category):
            os.mkdir(category)
        
        if isinstance(files, dict):
            files = list(itertools.chain.from_iterable(files.values()))

        for file in files:

            if '/' in file['file_name']:
                print("deep path, skipping: {}".format(file['file_name']))
                continue

            if file['file_name'].rpartition('.')[2] in ('zip', 'bz2'):
                continue

            target = category + '/' + file['file_name']

            if not verify_md5sum(target, file['md5']):
                download_file(file['file_name'], target)

            print(target)

        print(category, len(files))


def calc_req_patches(all_files):

    v2p = defaultdict(set)

    for category, files in all_files.items():
        if not category.endswith('-patch'):
            continue

        if isinstance(files, dict):
            files = list(itertools.chain.from_iterable(files.values()))

        for file in files:

            ee = ["EE {}".format(x) for x in file.get('ee_versions', ())]
            ce = ["CE {}".format(x) for x in file.get('ce_versions', ())]

            for v in (ee + ce):
                v2p[v].add(file['file_name'])

            # print(file['file_name'], file.get('ee_versions'), file.get('ce_versions'))

    for version, patches in sorted(v2p.items()):
        print(version)
        for p in patches:
            print("\t{}".format(p))



def main():
    blob = requests.get('https://www.magentocommerce.com/products/downloads/info/json', auth=(MAGEID, TOKEN)).json()
    sync_everything(blob)
    # calc_req_patches(blob)


if __name__ == '__main__':
    main()