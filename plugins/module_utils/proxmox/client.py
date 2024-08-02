import dataclasses
import os
import typing

import proxmoxer.tools.tasks
import requests
import urllib3
from proxmoxer import ProxmoxAPI

from ansible_collections.pbtn.common.plugins.module_utils import (
    exceptions,
)


class ProxmoxClientException(exceptions.BaseInfraException):
    def __init__(
        self,
        msg: str,
    ) -> None:
        super().__init__(msg)


class ProxmoxClientValidationException(exceptions.ValueInfraException):
    pass


class ProxmoxTaskClientException(ProxmoxClientException):
    def __init__(
        self,
        msg: str,
        task_status: dict,
    ) -> None:
        super().__init__(msg)
        self.task_status = task_status


class ProxmoxApiClientException(ProxmoxClientException):
    def __init__(
        self,
        msg: str,
        code: int = None,
        error: str = None,
        content: str = None,
    ) -> None:
        super().__init__(msg)
        self.code = code
        self.error = error
        self.content = content


class Client:
    def __init__(
        self,
        host,
        username=None,
        password=None,
        token_id=None,
        token=None,
        verify_ssl=True,
    ):
        if not isinstance(host, str):
            raise exceptions.ValueInfraException("host is a mandatory string")
        if password is not None and (token or token_id):
            raise exceptions.ValueInfraException(
                "if password is used token must be empty"
            )
        elif password is not None and not username:
            raise exceptions.ValueInfraException(
                "if password is provided username is mandatory"
            )
        username = username or (
            token_id.split("!")[0] if token_id and "!" in token_id else None
        )
        if token_id and "!" in token_id:
            token_id = token_id.split("!")[1]

        # todo, consider removing this and let the noise output show up
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            self.__api = ProxmoxAPI(
                host,
                user=username,
                password=password,
                token_name=token_id,
                token_value=token,
                verify_ssl=verify_ssl,
            )
        except requests.RequestException as err:
            raise ProxmoxApiClientException(
                "failed to connect to the PVE host", error=str(err)
            ) from err

    def wait_task(self, task_id: str):
        task_status = proxmoxer.tools.tasks.Tasks.blocking_status(self.__api, task_id)
        if "exitstatus" in task_status and task_status["exitstatus"].lower() != "ok":
            raise ProxmoxTaskClientException(task_status["exitstatus"], task_status)

    def node(self, name: str) -> "NodeClient":
        return NodeClient(name, self)

    def _resource_call(
        self, method: str, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        try:
            return_data = getattr(self.__api, method)(bare_url, **kwargs)
            is_upid = isinstance(return_data, str) and return_data.lower().startswith(
                "upid"
            )
            if wait and not is_upid:
                raise ProxmoxClientValidationException(
                    "request expected a task id to wait for but returned unexpected data"
                )
            elif wait:
                # if the caller sets the wait flag we assume
                # that the post returns a taskid
                self.wait_task(return_data)
            return return_data
        except proxmoxer.ResourceException as err:
            raise ProxmoxApiClientException(
                f"error performing a {method} call to {bare_url}",
                content=err.content,
                error=err.errors,
                code=err.status_code,
            ) from err
        except proxmoxer.AuthenticationError as err:
            raise ProxmoxApiClientException(
                f"authentication error performing a {method} call to {bare_url}",
                error=err.msg,
            ) from err
        except requests.RequestException as err:
            raise ProxmoxApiClientException(
                "failed to connect to the PVE host", error=str(err)
            ) from err

    def resource_post(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self._resource_call("post", bare_url, wait=wait, **kwargs)

    def resource_put(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self._resource_call("put", bare_url, wait=wait, **kwargs)

    def resource_delete(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self._resource_call("delete", bare_url, wait=wait, **kwargs)

    def resource_get(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self._resource_call("get", bare_url, wait=wait, **kwargs)


class NodeClient:
    def __init__(self, node_name: str, client: Client):
        self.__node_name = node_name
        self.__client = client

    def node_resource_post(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self.__client.resource_post(
            self.__build_node_url(bare_url), wait=wait, **kwargs
        )

    def node_resource_put(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self.__client.resource_put(
            self.__build_node_url(bare_url), wait=wait, **kwargs
        )

    def node_resource_delete(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self.__client.resource_delete(
            self.__build_node_url(bare_url), wait=wait, **kwargs
        )

    def node_resource_get(
        self, bare_url: str, wait: bool = False, **kwargs: typing.Any
    ) -> typing.Any:
        return self.__client.resource_get(
            self.__build_node_url(bare_url), wait=wait, **kwargs
        )

    @property
    def client(self) -> Client:
        return self.__client

    @property
    def node(self) -> str:
        return self.__node_name

    def __build_node_url(self, url: str) -> str:
        return "nodes/{}/{}".format(self.__node_name, url.lstrip("/"))
