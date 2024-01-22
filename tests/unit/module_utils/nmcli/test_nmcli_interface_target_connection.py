import itertools
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_target_connection,
    nmcli_interface_types,
)


def __prepare_permute_queriers(
    mocker, connections: typing.List[typing.Dict[str, typing.Any]]
):
    queriers = []
    for permutation in itertools.permutations(connections, len(connections)):
        querier = mocker.Mock()
        querier.get_connections.return_value = permutation
        queriers.append(querier)
    return queriers


def test_target_connection_data_factory_build_conn_data_ether_basic_1_ok(mocker):
    """
    Tests that the factory is able to pick a unique existing connection that matches
    the config by name of the connection.
    :param mocker:
    :return:
    """

    target_uuid = "69de43fc-6504-4a6e-a6aa-d04ffb5adb0e"
    target_conn_name = "testing-conn-name"

    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": target_conn_name,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": target_uuid,
            },
            # Ensure we prioritize active connections. This one is not picked
            # just because it is not active, like the target one
            {
                "connection.id": target_conn_name,
                "connection.type": "802-3-ethernet",
                "connection.uuid": "694bacc5-f167-47bd-8688-bb4a83067cba",
            },
            # Ensure the type cares if matching by name. This connection should
            # not be picked as it's not an ethernet one (the requested one)
            {
                "connection.id": target_conn_name,
                "connection.type": "vlan",
                "connection.uuid": "b15bd50c-c613-4fca-9303-8db4cc14a876",
                "connection.interface-name": "eth0",
            },
            # Shouldn't be picked as it's name doesn't match
            {
                "connection.id": "testing-conn",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "763f90fe-1c84-4f33-9e65-825f1e30cd1e",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            nmcli_interface_types.NetworkManagerConfiguratorOptions(),
            mocker.Mock(),
        )
        conn_config_raw = {
            "type": "ethernet",
            "iface": "eth0",
        }
        conn_config = net_config.EthernetConnectionConfig(
            conn_name=target_conn_name,
            raw_config=conn_config_raw,
            ip_links=[],
            connection_config_factory=mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert not result.empty
        assert result.uuids() == {target_uuid}
        assert len(result.uuids()) == 1
        assert result[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID] == target_uuid
        assert result.conn_config == conn_config


def test_target_connection_data_factory_build_conn_data_ether_basic_2_ok(mocker):
    """
    Tests that the factory is able to pick a unique existing connection that matches
    the config by interface of the connection.
    :param mocker:
    :return:
    """

    target_uuid = "69de43fc-6504-4a6e-a6aa-d04ffb5adb0e"
    target_conn_name = "testing-conn-name"
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": "testing-conn-55",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "763f90fe-1c84-4f33-9e65-825f1e30cd1e",
                "connection.interface-name": "eth0",
            },
            {
                "connection.id": "testing-conn-66",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "52deb66b-9672-4b48-817e-fe1e95985781",
                "connection.interface-name": "eth0",
                "general.state": "activated",
                "connection.master": "b5c2bdfb-5a23-42fa-bb58-4a274ac71bea",
            },
            {
                "connection.id": target_conn_name,
                "connection.type": "802-3-ethernet",
                "connection.uuid": target_uuid,
                "connection.interface-name": "eth0",
                "general.state": "activated",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            nmcli_interface_types.NetworkManagerConfiguratorOptions(),
            mocker.Mock(),
        )

        conn_config = net_config.EthernetConnectionConfig(
            conn_name="new-conn-name",
            raw_config={
                "type": "ethernet",
                "iface": "eth0",
            },
            ip_links=[],
            connection_config_factory=mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert not result.empty
        assert result.uuids() == {target_uuid}
        assert len(result.uuids()) == 1
        assert result[nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID] == target_uuid
        assert result.conn_config == conn_config
