import os

import urllib3
from ansible_collections.pbtn.common.plugins.module_utils.proxmox import (
    client,
)


def storage_delete(
    node_client: client.NodeClient,
    storage: str,
    volid: str = None,
    name: str = None,
    content_type: str = None,
):
    node_client.node_resource_delete(
        "storage/{}/content/{}".format(
            storage,
            __build_volid(
                volid=volid, storage=storage, content_type=content_type, name=name
            ),
        ),
        wait=True,
    )


def storage_list(node_client: client.NodeClient, storage: str):
    return node_client.node_resource_get("storage/{}/content".format(storage))


def storage_get(
    node_client: client.NodeClient,
    storage: str,
    name: str = None,
    content_type: str = None,
    volid: str = None,
):
    return node_client.node_resource_get(
        "storage/{}/content/{}".format(
            storage,
            __build_volid(
                volid=volid, storage=storage, content_type=content_type, name=name
            ),
        ),
    )


def storage_exists(
    node_client: client.NodeClient,
    storage: str,
    name: str = None,
    content_type: str = None,
    volid: str = None,
) -> bool:
    volid = __build_volid(
        volid=volid, storage=storage, content_type=content_type, name=name
    )
    return any(
        (data.get("volid", None) == volid)
        for data in storage_list(node_client, storage)
    )


def storage_create(
    node_client: client.NodeClient,
    storage: str,
    content_type: str,
    source: str,
    name: str = None,
    sha1_sum: str = None,
):
    url = urllib3.util.parse_url(source)
    if url.scheme is not None:
        filename = name or os.path.basename(url.path)
        __storage_create_from_url(
            node_client, storage, content_type, source, filename, sha1_sum=sha1_sum
        )
    else:
        __storage_create_from_file(node_client, storage, content_type, source)


def __storage_create_from_url(
    node_client: client.NodeClient,
    storage: str,
    content_type: str,
    url: str,
    filename: str,
    sha1_sum: str = None,
):
    hash_args = {}
    if sha1_sum:
        hash_args.update({"checksum": sha1_sum, "checksum-algorithm": "sha1"})
    node_client.node_resource_post(
        "storage/{}/download-url".format(storage),
        wait=True,
        url=url,
        content=content_type,
        filename=filename,
        **hash_args,
    )


def __storage_create_from_file(
    node_client: client.NodeClient,
    storage: str,
    content_type: str,
    filename: str,
):
    if not os.path.isfile(filename):
        raise client.ProxmoxClientValidationException(
            "file does not exist", field="source", value=filename
        )

    # Note: although the API defines a checksum field it looks like the versio we use to test doesn't
    # properly handle it. Skip passing the checksum for file uploads
    with open(filename, "rb") as f:
        node_client.node_resource_post(
            "storage/{}/upload".format(storage),
            wait=True,
            filename=f,
            content=content_type,
        )


def __build_volid(
    volid: str = None,
    storage: str = None,
    name: str = None,
    content_type: str = None,
) -> str:
    if not volid and not (name and content_type):
        raise client.ProxmoxClientValidationException(
            "if volid not given content_type and name are mandatory",
            field="name" if not name else "content_type",
        )
    return volid or "{}:{}/{}".format(storage, content_type, name)
