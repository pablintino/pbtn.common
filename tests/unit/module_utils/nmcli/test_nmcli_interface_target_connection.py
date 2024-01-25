import itertools
import typing

from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_target_connection,
)

from tests.unit.module_utils.test_utils import config_stub_data


def __build_testing_config_factory(
    mocker,
) -> net_config.ConnectionConfigFactory:
    mocked_ip_interface = mocker.Mock()
    mocked_ip_interface.get_ip_links.return_value = config_stub_data.TEST_IP_LINKS
    return net_config.ConnectionConfigFactory(mocked_ip_interface)


def __check_slave_conn_id_not_present(
    conn_id: str, result: nmcli_interface_target_connection.TargetConnectionData
):
    assert next(
        (
            conn_data
            for conn_data in result.slave_connections
            if conn_data.conn_config.name == conn_id
        )
    ).empty


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
    :param mocker: The pytest mocker fixture
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
    :param mocker: The pytest mocker fixture
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
            querier, mocker.Mock()
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


def test_target_connection_data_factory_build_conn_data_ether_basic_3_ok(mocker):
    """
    Tests that the factory is able to handle the case when no connection can be
    picked as there is no direct match and no match by interface
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    queriers = __prepare_permute_queriers(
        mocker,
        [
            # Tempt the logic to pick up this one. Wrong interface name.
            {
                "connection.id": "testing-conn-001",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "dee81746-a627-452d-8af8-999e6dcfc83f",
                "connection.interface-name": "eth0",
                "general.state": "activated",
            },
            # Tempt the logic to pick up this one as is active, but the type
            # is not of the same time and should be discarded.
            {
                "connection.id": "testing-conn-001",
                "connection.type": "vlan",
                "connection.uuid": "3db1fc19-1b98-46a7-b549-8ad14f5848ec",
                "connection.interface-name": "eth1",
                "general.state": "activated",
            },
            # Tempt the logic to pick up this one as it's the same type, but
            # it's not active.
            {
                "connection.id": "testing-conn-002",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "03adae0d-2224-47a7-a115-4e7583cd0e85",
                "connection.interface-name": "eth1",
            },
            # Tempt the logic to pick up this one, but it's a slave of another
            # connection, and we are trying to match the main connections
            {
                "connection.id": "testing-conn-002",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "03adae0d-2224-47a7-a115-4e7583cd0e85",
                "connection.interface-name": "eth1",
                "general.state": "activated",
                "connection.master": "1f561874-4367-40c3-abaf-6fa63cf991a9",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
        )

        conn_config = net_config.EthernetConnectionConfig(
            conn_name="non-existing-conn-name",
            raw_config={
                "type": "ethernet",
                "iface": "eth1",
            },
            ip_links=[],
            connection_config_factory=mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert result.empty
        assert not result.uuids()
        assert len(result.uuids()) == 0
        assert result.conn_config == conn_config


def test_target_connection_data_factory_build_conn_data_bridge_basic_1_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with all
    connection filled by exact occurrence of their names.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_conn_id = "bridge-conn"
    ether_conn_id_1 = "ether-conn-1"
    ether_conn_id_2 = "ether-conn-2"
    ether_conn_uuid_1 = "079fbb68-bfee-40fd-8216-ef4d9b96e563"
    ether_conn_uuid_2 = "c692d26b-e3ff-40da-997a-7a3ae87ef428"
    bridge_conn_uuid = "055812f8-2f2a-4239-886d-0e4a16633186"
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": bridge_conn_id,
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": bridge_conn_uuid,
            },
            {
                "connection.id": ether_conn_id_1,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": ether_conn_uuid_1,
            },
            {
                "connection.id": ether_conn_id_2,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": ether_conn_uuid_2,
            },
            # Tempt the logic to pick this one instead of
            # the direct match by name for the first slave
            {
                "connection.id": "ether-conn-001",
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.interface-name": "eth0",
                "connection.uuid": "b03d9a8e-836f-4615-8ded-cce5085e26a2",
            },
            # Tempt the logic to pick this one instead of
            # the direct match by name for the second slave
            {
                "connection.id": "ether-conn-002",
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.interface-name": "eth1",
                "connection.uuid": "f4240bb3-0f8a-40ad-823b-7ed7806d7a0b",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
        )

        conn_config = net_config.BridgeConnectionConfig(
            conn_name=bridge_conn_id,
            raw_config={
                "type": "bridge",
                "slaves": {
                    ether_conn_id_1: {"type": "ethernet", "iface": "eth0"},
                    ether_conn_id_2: {"type": "ethernet", "iface": "eth1"},
                },
            },
            ip_links=[],
            connection_config_factory=__build_testing_config_factory(mocker),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids()) == 3
        assert all(not slave_conn.empty for slave_conn in result.slave_connections)
        assert bridge_conn_uuid in result.uuids()
        assert ether_conn_uuid_1 in result.uuids()
        assert ether_conn_uuid_2 in result.uuids()


def test_target_connection_data_factory_build_conn_data_bridge_basic_2_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with only
    the slaves filled.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    ether_conn_id_1 = "ether-conn-1"
    ether_conn_id_2 = "ether-conn-2"
    ether_conn_uuid_1 = "079fbb68-bfee-40fd-8216-ef4d9b96e563"
    ether_conn_uuid_2 = "c692d26b-e3ff-40da-997a-7a3ae87ef428"
    queriers = __prepare_permute_queriers(
        mocker,
        [
            # Tempt the factory with a non-matching main connection
            {
                "connection.id": "bridge-conn-001",
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": "56b6ecb1-3132-4132-8109-a765c54ae64b",
            },
            # Tempt the factory with a non-matching main connection (by interface)
            {
                "connection.id": "bridge-conn-002",
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.interface-name": "br0",
                "connection.uuid": "9406a58e-1d19-4ec6-aaf6-df7e62f06d21",
            },
            # Tempt the factory with a non-matching main connection (by interface)
            # This time not active
            {
                "connection.id": "bridge-conn-003",
                "connection.type": "bridge",
                "connection.interface-name": "br1",
                "connection.uuid": "0796dc7f-0b85-4242-8a52-98d66ffedcfc",
            },
            {
                "connection.id": ether_conn_id_1,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": ether_conn_uuid_1,
            },
            {
                "connection.id": ether_conn_id_2,
                "connection.type": "802-3-ethernet",
                # Test that it picks up it even if inactive
                "connection.uuid": ether_conn_uuid_2,
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
        )

        conn_config = net_config.BridgeConnectionConfig(
            conn_name="bridge-conn",
            raw_config={
                "type": "bridge",
                "iface": "br1",
                "slaves": {
                    ether_conn_id_1: {"type": "ethernet", "iface": "eth0"},
                    ether_conn_id_2: {"type": "ethernet", "iface": "eth1"},
                },
            },
            ip_links=[],
            connection_config_factory=__build_testing_config_factory(mocker),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert result.empty
        assert result.uuid is None
        assert result.conn_config == conn_config
        assert len(result.uuids()) == 2
        assert all(not slave_conn.empty for slave_conn in result.slave_connections)
        assert ether_conn_uuid_1 in result.uuids()
        assert ether_conn_uuid_2 in result.uuids()


def test_target_connection_data_factory_build_conn_data_bridge_basic_3_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with only
    the slave connection missing.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_conn_id = "bridge-conn"
    ether_conn_id_1 = "ether-conn-1"
    ether_conn_id_2 = "ether-conn-2"
    ether_conn_uuid_1 = "079fbb68-bfee-40fd-8216-ef4d9b96e563"
    bridge_conn_uuid = "055812f8-2f2a-4239-886d-0e4a16633186"
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": bridge_conn_id,
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": bridge_conn_uuid,
            },
            # Tempt the logic with a connection that doesn't
            # match by name
            {
                "connection.id": "bridge-connection-1",
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": bridge_conn_uuid,
            },
            {
                "connection.id": ether_conn_id_1,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": ether_conn_uuid_1,
            },
            # Tempt the logic with a non-matching slave (wrong interface)
            {
                "connection.id": "ether-conn-001",
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                # Same as conn-1. Should not be picked by any connections.
                "connection.interface-name": "eth0",
                "connection.uuid": "b1c4d95c-495d-483f-a09b-238bd8e8d698",
            },
            # Tempt the logic with a connection with inactive interface
            {
                "connection.id": "ether-conn-002",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "eth1",
                "connection.uuid": "1464f43f-c6c4-4047-937c-55cb30f06ad0",
            },
            # Tempt the logic with a connection of the wrong type
            {
                "connection.id": "vlan-conn-003",
                "connection.type": "vlan",
                "connection.interface-name": "eth1",
                "general.state": "activated",
                "connection.uuid": "fbe581fd-437d-47ff-9a36-995708a7c97b",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
        )

        conn_config = net_config.BridgeConnectionConfig(
            conn_name=bridge_conn_id,
            raw_config={
                "type": "bridge",
                "slaves": {
                    ether_conn_id_1: {"type": "ethernet", "iface": "eth0"},
                    ether_conn_id_2: {"type": "ethernet", "iface": "eth1"},
                },
            },
            ip_links=[],
            connection_config_factory=__build_testing_config_factory(mocker),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids()) == 2
        assert bridge_conn_uuid in result.uuids()
        assert ether_conn_uuid_1 in result.uuids()
        __check_slave_conn_id_not_present(ether_conn_id_2, result)


def test_target_connection_data_factory_build_conn_data_bridge_basic_4_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with all
    connections matching using the interface name as ID.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_conn_id = "bridge-conn-1"
    ether_conn_id_1 = "ether-conn-1"
    ether_conn_uuid_1 = "079fbb68-bfee-40fd-8216-ef4d9b96e563"
    ether_conn_uuid_2 = "c692d26b-e3ff-40da-997a-7a3ae87ef428"
    bridge_conn_uuid = "055812f8-2f2a-4239-886d-0e4a16633186"
    queriers = __prepare_permute_queriers(
        mocker,
        [
            # Tempt the factory with a non-matching main connection
            {
                "connection.id": "bridge-conn-001",
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": "56b6ecb1-3132-4132-8109-a765c54ae64b",
            },
            # Tempt the factory with a non-matching main connection
            # The interface name does not match
            {
                "connection.id": "bridge-conn-002",
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.interface-name": "br0",
                "connection.uuid": "56b6ecb1-3132-4132-8109-a765c54ae64b",
            },
            {
                "connection.id": bridge_conn_id,
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.interface-name": "br123",
                "connection.uuid": bridge_conn_uuid,
            },
            {
                "connection.id": ether_conn_id_1,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": ether_conn_uuid_1,
            },
            {
                "connection.id": "ether-conn-001",
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.interface-name": "eth1",
                "connection.uuid": ether_conn_uuid_2,
            },
            # Tempt the logic to pick up this connection that is not active
            {
                "connection.id": "ether-conn-002",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "eth1",
                "connection.uuid": "eb9fde83-9dd8-40f6-b648-617a032d9692",
            },
            # Tempt the logic to pick up this connection that is not of
            # the expected type
            {
                "connection.id": "vlan-conn-003",
                "connection.type": "vlan",
                "connection.interface-name": "eth1",
                "general.state": "activated",
                "connection.uuid": "d0fce916-e712-43f2-b13a-7a6fe427ead0",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
        )

        conn_config = net_config.BridgeConnectionConfig(
            conn_name="non-existing-bridge-conn",
            raw_config={
                "type": "bridge",
                "iface": "br123",
                "slaves": {
                    ether_conn_id_1: {"type": "ethernet", "iface": "eth0"},
                    "dont-care-conn-1": {"type": "ethernet", "iface": "eth1"},
                },
            },
            ip_links=[],
            connection_config_factory=__build_testing_config_factory(mocker),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids()) == 3
        assert all(not slave_conn.empty for slave_conn in result.slave_connections)
        assert bridge_conn_uuid in result.uuids()
        assert ether_conn_uuid_1 in result.uuids()
        assert ether_conn_uuid_2 in result.uuids()


def test_target_connection_data_factory_build_conn_data_bridge_basic_5_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with no
    matches for the slave connections.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_conn_id = "bridge-conn"
    ether_conn_id_1 = "ether-conn-1"
    ether_conn_id_2 = "ether-conn-2"
    bridge_conn_uuid = "055812f8-2f2a-4239-886d-0e4a16633186"
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": bridge_conn_id,
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": bridge_conn_uuid,
            },
            # Tempt with a wrong type connection
            {
                "connection.id": "vlan-conn-001",
                "connection.type": "vlan",
                "connection.interface-name": "eth1",
                "general.state": "activated",
                "connection.uuid": "d0fce916-e712-43f2-b13a-7a6fe427ead0",
            },
            # Tempt with an inactive connection
            {
                "connection.id": "ether-conn-001",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "eth1",
                "connection.uuid": "803ed520-e323-41d6-bab4-fe06f86afacf",
            },
            # Tempt with a non-matching interface name
            {
                "connection.id": "ether-conn-002",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "eth3",
                "general.state": "activated",
                "connection.uuid": "08289f91-cf1e-4187-8ef4-4a53883dc67d",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
        )

        conn_config = net_config.BridgeConnectionConfig(
            conn_name=bridge_conn_id,
            raw_config={
                "type": "bridge",
                "slaves": {
                    ether_conn_id_1: {"type": "ethernet", "iface": "eth0"},
                    ether_conn_id_2: {"type": "ethernet", "iface": "eth1"},
                },
            },
            ip_links=[],
            connection_config_factory=__build_testing_config_factory(mocker),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids()) == 1
        assert bridge_conn_uuid in result.uuids()
        __check_slave_conn_id_not_present(ether_conn_id_1, result)
        __check_slave_conn_id_not_present(ether_conn_id_2, result)


def test_target_connection_data_factory_build_conn_data_bridge_basic_6_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with no
    matches for any connection.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": "bridge-conn-001",
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": "7f9a4062-4cd3-45f3-b8f0-7c20ede1b25a",
            },
            {
                "connection.id": "ether-conn-000",
                "connection.type": "802-3-ethernet",
                # It may not make sense to call and ethernet iface br1,
                # but it does the job for the purpose of this test
                "connection.interface-name": "br1",
                "general.state": "activated",
                "connection.uuid": "24d6b14d-98fe-4277-b4de-5ed78a5e7922",
            },
            # Tempt the logic with an inactive main connection
            {
                "connection.id": "bridge-conn-001",
                "connection.type": "bridge",
                "connection.interface-name": "br1",
                "connection.uuid": "d4c42a1a-464b-4e9e-907e-ec7f5414621f",
            },
            # Tempt the logic with a connection of the wrong type for the second
            # slave connection
            {
                "connection.id": "vlan-conn-001",
                "connection.type": "vlan",
                "connection.interface-name": "eth1",
                "general.state": "activated",
                "connection.uuid": "d0fce916-e712-43f2-b13a-7a6fe427ead0",
            },
            # Tempt the logic with an inactive connection for the second slave
            {
                "connection.id": "ether-conn-001",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "eth1",
                "connection.uuid": "803ed520-e323-41d6-bab4-fe06f86afacf",
            },
            {
                "connection.id": "ether-conn-002",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "eth3",
                "general.state": "activated",
                "connection.uuid": "08289f91-cf1e-4187-8ef4-4a53883dc67d",
            },
        ],
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
        )

        conn_config = net_config.BridgeConnectionConfig(
            conn_name="non-existing-bridge-conn-1",
            raw_config={
                "type": "bridge",
                "iface": "br1",
                "slaves": {
                    "ether-conn-1": {"type": "ethernet", "iface": "eth0"},
                    "ether-conn-2": {"type": "ethernet", "iface": "eth1"},
                },
            },
            ip_links=[],
            connection_config_factory=__build_testing_config_factory(mocker),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(
            result, nmcli_interface_target_connection.TargetConnectionData
        )
        assert result.empty
        assert result.conn_config == conn_config
        assert not result.uuids()
        assert all(slave_conn.empty for slave_conn in result.slave_connections)
