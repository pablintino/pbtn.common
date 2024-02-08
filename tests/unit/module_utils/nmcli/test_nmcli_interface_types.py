import collections.abc

import pytest


from ansible_collections.pablintino.base_infra.plugins.module_utils import (
    exceptions,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_interface_types,
)


def test_nmcli_types_configurable_connection_data_fields_ok(mocker):
    conn_data = {"connection.uuid": "18f9d3e4-0e2f-4222-82f2-57b13b4d0bbe"}
    conn_config_target = net_config.EthernetConnectionConfig(
        conn_name="ether-conn-1",
        raw_config={
            "type": "ethernet",
            "iface": "eth1",
        },
        ip_links=[],
        connection_config_factory=mocker.Mock(),
    )
    configurable_conn_data = nmcli_interface_types.ConfigurableConnectionData(
        conn_data, conn_config_target
    )
    assert not configurable_conn_data.empty
    assert isinstance(configurable_conn_data, collections.abc.Mapping)
    # Check that the ConfigurableConnectionData len can be called
    assert len(configurable_conn_data) == len(conn_data)
    # Check that the ConfigurableConnectionData can be accessed as an iterator
    assert next(iter(configurable_conn_data)) == next(iter(conn_data.keys()))
    assert configurable_conn_data.uuid == conn_data["connection.uuid"]
    # Check that the ConfigurableConnectionData can be accessed as a mapping
    assert configurable_conn_data["connection.uuid"] == conn_data["connection.uuid"]
    assert configurable_conn_data.conn_config == conn_config_target

    configurable_conn_data_empty = nmcli_interface_types.ConfigurableConnectionData(
        None, conn_config_target
    )
    assert configurable_conn_data_empty.empty

    with pytest.raises(exceptions.ValueInfraException) as err:
        nmcli_interface_types.ConfigurableConnectionData(conn_data, None)
    assert "must be provided" in str(err.value)
