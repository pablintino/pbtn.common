import collections.abc
import itertools
import typing

import mock
from ansible_collections.pablintino.base_infra.plugins.module_utils.net import (
    net_config,
)
from ansible_collections.pablintino.base_infra.plugins.module_utils.nmcli import (
    nmcli_constants,
    nmcli_interface_target_connection,
    nmcli_interface_types,
)

from ansible_collections.pablintino.base_infra.tests.unit.module_utils.test_utils import (
    net_config_stub,
)


def __check_slave_conn_id_not_present(
    conn_id: str, result: nmcli_interface_types.TargetConnectionData
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


def __test_build_delete_conn_list_from_mocks(
    querier,
    mocker,
    target_connection_data: nmcli_interface_types.TargetConnectionData,
    expected_uuids: typing.List[str],
    config_handler_connections: typing.List[net_config.MainConnectionConfig] = None,
    config_session_uuids: typing.Sequence[str] = None,
):
    with mock.patch(
        "ansible_collections.pablintino.base_infra.plugins.module_utils."
        "net.net_config.ConnectionsConfigurationHandler.connections",
        new_callable=mock.PropertyMock,
    ) as mock_connections, mock.patch(
        "ansible_collections.pablintino.base_infra.plugins.module_utils."
        "nmcli.nmcli_interface_types.ConfigurationSession.uuids",
        new_callable=mock.PropertyMock,
    ) as mock_config_session:
        mock_connections.return_value = config_handler_connections or []
        mock_config_session.return_value = config_session_uuids or []
        mocked_handler = net_config.ConnectionsConfigurationHandler({}, mocker.Mock())
        mocked_config_session = nmcli_interface_types.ConfigurationSession()
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocked_handler,
            mocked_config_session,
        )
        conns_list = factory.build_delete_conn_list(target_connection_data)
        assert isinstance(conns_list, collections.abc.Sequence)
        assert len(conns_list) == len(expected_uuids)
        for conn_data in conns_list:
            assert isinstance(conn_data, collections.abc.Mapping)
            conn_uuid = conn_data.get(
                nmcli_constants.NMCLI_CONN_FIELD_CONNECTION_UUID, None
            )
            assert conn_uuid in expected_uuids


def test_target_connection_data_factory_build_conn_data_ether_basic_1_ok(mocker):
    """
    Tests that the factory is able to pick a unique existing connection that matches
    the config by name of the connection.
    :param mocker: The pytest mocker fixture
    """

    target_uuid = "69de43fc-6504-4a6e-a6aa-d04ffb5adb0e"
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state=None
    )
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": conn_config.name,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": target_uuid,
            },
            # Ensure we prioritize active connections. This one is not picked
            # just because it is not active, like the target one
            {
                "connection.id": conn_config.name,
                "connection.type": "802-3-ethernet",
                "connection.uuid": "694bacc5-f167-47bd-8688-bb4a83067cba",
            },
            # Ensure the type cares if matching by name. This connection should
            # not be picked as it's not an ethernet one (the requested one)
            {
                "connection.id": conn_config.name,
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
            mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert not result.empty
        assert len(result.uuids) == 1
        assert next(iter(result.uuids)) == target_uuid
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
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state=None
    )
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
            mocker.Mock(),
            mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert not result.empty
        assert len(result.uuids) == 1
        assert next(iter(result.uuids)) == target_uuid
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
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=1, state=None, conn_name="non-existing-conn-name"
    )
    for querier in queriers:
        factory = nmcli_interface_target_connection.TargetConnectionDataFactory(
            querier,
            mocker.Mock(),
            mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert result.empty
        assert not result.uuids
        assert len(result.uuids) == 0
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
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=2, start_index=0
    )
    ether_conn_uuid_1 = "079fbb68-bfee-40fd-8216-ef4d9b96e563"
    ether_conn_uuid_2 = "c692d26b-e3ff-40da-997a-7a3ae87ef428"
    bridge_conn_uuid = "055812f8-2f2a-4239-886d-0e4a16633186"
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": conn_config.name,
                "connection.type": "bridge",
                "general.state": "activated",
                "connection.uuid": bridge_conn_uuid,
            },
            {
                "connection.id": conn_config.slaves[0].name,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": ether_conn_uuid_1,
            },
            {
                "connection.id": conn_config.slaves[1].name,
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
            mocker.Mock(),
        )

        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids) == 3
        assert all(not slave_conn.empty for slave_conn in result.slave_connections)
        assert bridge_conn_uuid in result.uuids
        assert ether_conn_uuid_1 in result.uuids
        assert ether_conn_uuid_2 in result.uuids


def test_target_connection_data_factory_build_conn_data_bridge_basic_2_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with only
    the slaves filled.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    ether_conn_uuid_1 = "079fbb68-bfee-40fd-8216-ef4d9b96e563"
    ether_conn_uuid_2 = "c692d26b-e3ff-40da-997a-7a3ae87ef428"
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=2, start_index=1
    )
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
                "connection.id": conn_config.slaves[0].name,
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.uuid": ether_conn_uuid_1,
            },
            {
                "connection.id": conn_config.slaves[1].name,
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
            mocker.Mock(),
        )

        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert result.empty
        assert result.uuid is None
        assert result.conn_config == conn_config
        assert len(result.uuids) == 2
        assert all(not slave_conn.empty for slave_conn in result.slave_connections)
        assert ether_conn_uuid_1 in result.uuids
        assert ether_conn_uuid_2 in result.uuids


def test_target_connection_data_factory_build_conn_data_bridge_basic_3_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with only
    the slave connection missing.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    ether_conn_uuid_1 = "079fbb68-bfee-40fd-8216-ef4d9b96e563"
    bridge_conn_uuid = "055812f8-2f2a-4239-886d-0e4a16633186"
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=2, start_index=0
    )
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": conn_config.name,
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
                "connection.id": conn_config.slaves[0].name,
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
            mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids) == 2
        assert bridge_conn_uuid in result.uuids
        assert ether_conn_uuid_1 in result.uuids
        __check_slave_conn_id_not_present(conn_config.slaves[1].name, result)


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
            connection_config_factory=net_config_stub.build_testing_config_factory(
                mocker
            ),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids) == 3
        assert all(not slave_conn.empty for slave_conn in result.slave_connections)
        assert bridge_conn_uuid in result.uuids
        assert ether_conn_uuid_1 in result.uuids
        assert ether_conn_uuid_2 in result.uuids


def test_target_connection_data_factory_build_conn_data_bridge_basic_5_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with no
    matches for the slave connections.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_conn_uuid = "055812f8-2f2a-4239-886d-0e4a16633186"
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=2, start_index=0
    )
    queriers = __prepare_permute_queriers(
        mocker,
        [
            {
                "connection.id": conn_config.name,
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
            mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert not result.empty
        assert result.uuid == bridge_conn_uuid
        assert result.conn_config == conn_config
        assert len(result.uuids) == 1
        assert bridge_conn_uuid in result.uuids
        __check_slave_conn_id_not_present(conn_config.slaves[0].name, result)
        __check_slave_conn_id_not_present(conn_config.slaves[1].name, result)


def test_target_connection_data_factory_build_conn_data_bridge_basic_6_ok(mocker):
    """
    Tests that the factory is able to handle a main-slave connection with no
    matches for any connection.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    conn_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=2, start_index=0
    )
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
            mocker.Mock(),
        )
        result = factory.build_target_connection_data(conn_config)
        assert isinstance(result, nmcli_interface_types.TargetConnectionData)
        assert result.empty
        assert result.conn_config == conn_config
        assert not result.uuids
        assert all(slave_conn.empty for slave_conn in result.slave_connections)


def test_target_connection_data_factory_build_delete_conn_list_1_ok(mocker):
    """
    Test that the delete list if properly build in cases without slave connections.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    ether_conn_id = "ether-conn-001"
    connection_data_raw = {
        "connection.id": ether_conn_id,
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.uuid": "98ef06cf-a80e-4771-ad96-8375b123c8a7",
    }
    conn_config = net_config_stub.build_testing_ether_config(
        mocker, index=0, state=None, conn_name=ether_conn_id
    )
    target_connection_data = nmcli_interface_types.TargetConnectionData.Builder(
        connection_data_raw, conn_config
    ).build()
    to_remove_uuid_1 = "b15bd50c-c613-4fca-9303-8db4cc14a876"
    to_remove_uuid_2 = "6ffd5837-4274-4d3f-b0d2-472400bbd3f3"
    to_remove_uuid_3 = "0e6ad240-f8ea-4fb2-82ea-e1737dad2556"
    queriers = __prepare_permute_queriers(
        mocker,
        [
            connection_data_raw,
            {
                "connection.id": "ether-conn-002",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "694bacc5-f167-47bd-8688-bb4a83067cba",
            },
            # Should be deleted as it's for the same interface, and it's not
            # the picked one
            {
                "connection.id": "ether-conn-003",
                "connection.type": "vlan",
                "connection.uuid": to_remove_uuid_1,
                "general.state": "activated",
                "connection.interface-name": "eth0",
            },
            # Should be deleted. Same as the previous but active. It shouldn't
            # care about the status of the connection.
            {
                "connection.id": "ether-conn-004",
                "connection.type": "vlan",
                "connection.uuid": to_remove_uuid_2,
                "connection.interface-name": "eth0",
            },
            # Shouldn't be picked up as it has not interface to relate
            # the connection to the targeted one
            {
                "connection.id": "testing-conn",
                "connection.type": "802-3-ethernet",
                "connection.uuid": "763f90fe-1c84-4f33-9e65-825f1e30cd1e",
            },
            # Should be deleted as we do not allow ID duplications
            {
                "connection.id": conn_config.name,
                "connection.type": "vlan",
                "connection.uuid": to_remove_uuid_3,
                "connection.interface-name": "eth0",
            },
        ],
    )
    for querier in queriers:
        __test_build_delete_conn_list_from_mocks(
            querier,
            mocker,
            target_connection_data,
            [to_remove_uuid_1, to_remove_uuid_2, to_remove_uuid_3],
        )


def test_target_connection_data_factory_build_delete_conn_list_2_ok(mocker):
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_uuid_1 = "98ef06cf-a80e-4771-ad96-8375b123c8a7"
    vlan_uuid_1 = "f7e59009-1367-47e9-9414-ac35b89ec8a4"
    ether_uuid_1 = "ceb771f1-b183-4ce4-89be-95bea292d917"
    ether_uuid_2 = "10ba7df7-ed98-4e00-b128-a26919640fb2"
    connection_data_raw_bridge = {
        "connection.id": "bridge-conn-1",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_1,
    }
    connection_data_raw_vlan_slave = {
        "connection.id": "vlan-conn-1",
        "connection.type": "vlan",
        "general.state": "activated",
        "connection.master": bridge_uuid_1,
        "connection.uuid": vlan_uuid_1,
    }
    connection_data_raw_ether = {
        "connection.id": "ether-conn-1",
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": "eth0",
        "connection.uuid": ether_uuid_1,
    }

    conn_config = net_config.BridgeConnectionConfig(
        conn_name="bridge-conn-001",
        raw_config={
            "type": "bridge",
            "iface": "br0",
            "slaves": {
                "vlan-conn-1": {
                    "type": "vlan",
                    "iface": "eth0.200",
                    "vlan": {
                        "id": 200,
                        "parent": "eth0",
                    },
                }
            },
        },
        ip_links=[],
        connection_config_factory=net_config_stub.build_testing_config_factory(mocker),
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge, conn_config
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_vlan_slave, conn_config.slaves[0]
            )
        )
        .build()
    )

    queriers = __prepare_permute_queriers(
        mocker,
        [
            connection_data_raw_bridge,
            connection_data_raw_vlan_slave,
            connection_data_raw_ether,
            # Should be deleted as it touches a related interface
            # and is not part of the config session
            {
                "connection.id": "ether-conn-2",
                "connection.type": "802-3-ethernet",
                "general.state": "activated",
                "connection.interface-name": "eth0",
                "connection.uuid": ether_uuid_2,
            },
        ],
    )
    for querier in queriers:
        __test_build_delete_conn_list_from_mocks(
            querier,
            mocker,
            target_connection_data,
            [ether_uuid_2],
            config_session_uuids=[ether_uuid_1],
        )


def test_target_connection_data_factory_build_delete_conn_list_3_ok(mocker):
    """
    Tests that the factory is able to build the to-delete connections list taking
    into account connections that will be configured afterward, like a bridge slave
    VLANs connection configured after their parent interface (the ethernet one).
    If connection data exists, for another connection, not yet configured,
    we should keep it.
    This test ensures this mechanism works for main-slave based connections.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_uuid_1 = "98ef06cf-a80e-4771-ad96-8375b123c8a7"
    vlan_uuid_1 = "f7e59009-1367-47e9-9414-ac35b89ec8a4"
    ether_uuid_1 = "ceb771f1-b183-4ce4-89be-95bea292d917"
    ether_uuid_2 = "10ba7df7-ed98-4e00-b128-a26919640fb2"
    ether_uuid_3 = "907355a9-3551-427e-b72c-0f69b509122c"
    connection_data_raw_bridge = {
        "connection.id": "bridge-conn-1",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_1,
    }
    connection_data_raw_vlan_slave = {
        "connection.id": "vlan-conn-1",
        "connection.type": "vlan",
        "general.state": "activated",
        "connection.master": bridge_uuid_1,
        "connection.interface-name": "eth1.200",
        "vlan.parent": "eth1",
        "connection.uuid": vlan_uuid_1,
    }
    connection_data_raw_ether = {
        "connection.id": "ether-conn-1",
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": "eth1",
        "connection.uuid": ether_uuid_1,
    }

    conn_config_target = net_config.EthernetConnectionConfig(
        conn_name="ether-conn-001",
        raw_config={
            "type": "ethernet",
            "iface": "eth1",
        },
        ip_links=[],
        connection_config_factory=mocker.Mock(),
    )
    conn_config_dependant = net_config.BridgeConnectionConfig(
        conn_name="bridge-conn-1",
        raw_config={
            "type": "bridge",
            "iface": "br0",
            "slaves": {
                "vlan-conn-1": {
                    "type": "vlan",
                    "iface": f"{conn_config_target.interface.iface_name}.200",
                    "vlan": {
                        "id": 200,
                        "parent": conn_config_target.interface.iface_name,
                    },
                }
            },
        },
        ip_links=[],
        connection_config_factory=net_config_stub.build_testing_config_factory(mocker),
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_ether, conn_config_target
        )
    ).build()
    queriers = __prepare_permute_queriers(
        mocker,
        [
            connection_data_raw_bridge,
            connection_data_raw_vlan_slave,
            connection_data_raw_ether,
            # Should be deleted as it touches a related interface
            # and is not part of the config session
            {
                "connection.id": "ether-conn-2",
                "connection.type": "802-3-ethernet",
                # Cannot be active as for that we have ether-conn-1
                # For this test we will make it active to test the protection
                # mechanism we have in place. The connection configuring the interface
                # is the one that wins and other candidates are never preserved.
                "general.state": "activated",
                "connection.interface-name": "eth1",
                "connection.uuid": ether_uuid_2,
            },
            # Should be deleted as it touches a related interface
            # and is not part of the config session
            {
                "connection.id": "ether-conn-3",
                "connection.type": "802-3-ethernet",
                "connection.interface-name": "eth1",
                "connection.uuid": ether_uuid_3,
            },
        ],
    )
    for querier in queriers:
        __test_build_delete_conn_list_from_mocks(
            querier,
            mocker,
            target_connection_data,
            [ether_uuid_2, ether_uuid_3],
            config_session_uuids=[ether_uuid_1],
            config_handler_connections=[conn_config_dependant, conn_config_target],
        )


def test_target_connection_data_factory_build_delete_conn_list_4_ok(mocker):
    """
    Tests that the factory is able to build the to-delete connections list taking
    into account connections that will be configured afterward, like a VLAN
    connection configured after their parent interface (the ethernet one).
    If connection data exists, for another connection, not yet configured,
    we should keep it.
    This test ensures this mechanism works for main-only based connections.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    vlan_uuid_1 = "f7e59009-1367-47e9-9414-ac35b89ec8a4"
    ether_uuid_1 = "ceb771f1-b183-4ce4-89be-95bea292d917"
    ether_uuid_2 = "10ba7df7-ed98-4e00-b128-a26919640fb2"
    connection_data_raw_vlan_slave = {
        "connection.id": "vlan-conn-1",
        "connection.type": "vlan",
        "general.state": "activated",
        "connection.interface-name": "eth1.200",
        "vlan.parent": "eth1",
        "connection.uuid": vlan_uuid_1,
    }
    connection_data_raw_ether = {
        "connection.id": "ether-conn-1",
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": "eth1",
        "connection.uuid": ether_uuid_1,
    }

    conn_config_target = net_config_stub.build_testing_ether_config(mocker, index=1)
    conn_config_dependant = net_config_stub.build_testing_vlan_config(
        mocker, vlan_id=200, index=1
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_ether, conn_config_target
        )
    ).build()
    queriers = __prepare_permute_queriers(
        mocker,
        [
            connection_data_raw_vlan_slave,
            connection_data_raw_ether,
            # Should be deleted as it touches a related interface
            # and is not part of the config session
            {
                "connection.id": "ether-conn-2",
                "connection.type": "802-3-ethernet",
                # Cannot be active as for that we have ether-conn-1
                # This test, that target the ether connection by name,
                # doesn't really care if it's active or not
                "connection.interface-name": "eth1",
                "connection.uuid": ether_uuid_2,
            },
        ],
    )
    for querier in queriers:
        __test_build_delete_conn_list_from_mocks(
            querier,
            mocker,
            target_connection_data,
            [ether_uuid_2],
            config_session_uuids=[ether_uuid_1],
            config_handler_connections=[conn_config_dependant, conn_config_target],
        )


def test_target_connection_data_factory_build_delete_conn_list_5_ok(mocker):
    """
    Tests that the factory is able to build the to-delete connections list taking
    into account the main connections, like bridges; that may have only one slave
    that will be deleted in place of another connection. If a main connection has
    no more slaves,the main connection should be deleted too.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_uuid_1 = "f7e59009-1367-47e9-9414-ac35b89ec8a4"
    bridge_uuid_2 = "6b2eeafe-3611-484e-b5a3-3696712c49e9"
    ether_uuid_1 = "ceb771f1-b183-4ce4-89be-95bea292d917"
    ether_uuid_2 = "faf7d96c-6317-4883-8acb-0a7b0b59ddc1"
    vlan_uuid_1 = "0243cae6-2ac5-442e-8386-d262f340ddcb"
    connection_data_raw_bridge_1 = {
        "connection.id": "bridge-conn-1",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_1,
    }
    # As it's slave connections (ether-conn-2 and vlan-conn-1)
    # will be deleted, this needs to be deleted too.
    connection_data_raw_bridge_2 = {
        "connection.id": "bridge-conn-2",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_2,
    }
    connection_data_raw_ether_1 = {
        "connection.id": "ether-conn-1",
        "connection.type": "802-3-ethernet",
        "connection.interface-name": "eth1",
        "connection.uuid": ether_uuid_1,
    }
    # This one should be deleted as it's a related interface
    # of ether-conn-1, but it's not the target one
    connection_data_raw_ether_2 = {
        "connection.id": "ether-conn-2",
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": "eth1",
        "connection.master": bridge_uuid_2,
        "connection.uuid": ether_uuid_2,
    }
    # This one should be deleted as it's a related interface
    # of ether-conn-1, but it's not the target one
    connection_data_raw_vlan_1 = {
        "connection.id": "vlan-conn-1",
        "connection.type": "vlan",
        "general.state": "activated",
        "connection.interface-name": "eth1.200",
        "vlan.parent": "eth1",
        "connection.master": bridge_uuid_2,
        "connection.uuid": vlan_uuid_1,
    }
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=1, start_index=1
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge_1, conn_config_target
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_ether_1, conn_config_target.slaves[0]
            )
        )
        .build()
    )
    queriers = __prepare_permute_queriers(
        mocker,
        [
            connection_data_raw_bridge_1,
            connection_data_raw_bridge_2,
            connection_data_raw_ether_1,
            connection_data_raw_ether_2,
            connection_data_raw_vlan_1,
        ],
    )
    for querier in queriers:
        __test_build_delete_conn_list_from_mocks(
            querier,
            mocker,
            target_connection_data,
            [bridge_uuid_2, ether_uuid_2, vlan_uuid_1],
        )


def test_target_connection_data_factory_build_delete_conn_list_6_ok(mocker):
    """
    Tests that the factory is able to build the to-delete connections list taking
    into account that if a main connection has connections that are no longer part
    of the configuration, like an old slave, those need to be deleted.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_uuid_1 = "f7e59009-1367-47e9-9414-ac35b89ec8a4"
    ether_uuid_1 = "ceb771f1-b183-4ce4-89be-95bea292d917"
    ether_uuid_2 = "93555842-8011-4ad5-b666-0f80f13a20dc"
    # The bridge we want to configure
    connection_data_raw_bridge_1 = {
        "connection.id": "bridge-conn-1",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_1,
    }
    # The ethernet connection the bridge will have
    connection_data_raw_ether_1 = {
        "connection.id": "ether-conn-1",
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": "eth1",
        "connection.uuid": ether_uuid_1,
    }
    # A no longer in use ethernet connection that should
    # be removed
    connection_data_raw_ether_2 = {
        "connection.id": "ether-conn-2",
        "connection.type": "802-3-ethernet",
        "general.state": "activated",
        "connection.interface-name": "eth0",
        "connection.master": bridge_uuid_1,
        "connection.uuid": ether_uuid_2,
    }
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=1, start_index=1
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge_1, conn_config_target
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_ether_1, conn_config_target.slaves[0]
            )
        )
        .build()
    )

    queriers = __prepare_permute_queriers(
        mocker,
        [
            connection_data_raw_bridge_1,
            connection_data_raw_ether_1,
            connection_data_raw_ether_2,
        ],
    )
    for querier in queriers:
        __test_build_delete_conn_list_from_mocks(
            querier,
            mocker,
            target_connection_data,
            [ether_uuid_2],
        )


def test_target_connection_data_factory_build_delete_conn_list_7_ok(mocker):
    """
    Tests that the factory is able to build the to-delete connections list taking
    into account that if a main connection loses all of its slaves the logic
    will take care of cleanup it.
    :param mocker: The pytest mocker fixture
    """
    # Create a list of queries with all the possible combinations
    # of connections order to ensure the result is not order
    # dependant
    bridge_uuid_1 = "f7e59009-1367-47e9-9414-ac35b89ec8a4"
    bridge_uuid_2 = "6b2eeafe-3611-484e-b5a3-3696712c49e9"
    ether_uuid_1 = "ceb771f1-b183-4ce4-89be-95bea292d917"
    connection_data_raw_bridge_1 = {
        "connection.id": "bridge-conn-1",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_1,
    }
    connection_data_raw_bridge_2 = {
        "connection.id": "bridge-conn-2",
        "connection.type": "bridge",
        "general.state": "activated",
        "connection.uuid": bridge_uuid_2,
    }
    connection_data_raw_ether_1 = {
        "connection.id": "ether-conn-1",
        "connection.type": "802-3-ethernet",
        "connection.interface-name": "eth1",
        "connection.master": bridge_uuid_2,
        "general.state": "activated",
        "connection.uuid": ether_uuid_1,
    }
    conn_config_target = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=1, start_index=1
    )
    target_connection_data = (
        nmcli_interface_types.TargetConnectionData.Builder(
            connection_data_raw_bridge_1, conn_config_target
        )
        .append_slave(
            nmcli_interface_types.ConfigurableConnectionData(
                connection_data_raw_ether_1, conn_config_target.slaves[0]
            )
        )
        .build()
    )

    queriers = __prepare_permute_queriers(
        mocker,
        [
            connection_data_raw_bridge_1,
            connection_data_raw_bridge_2,
            connection_data_raw_ether_1,
        ],
    )
    for querier in queriers:
        __test_build_delete_conn_list_from_mocks(
            querier,
            mocker,
            target_connection_data,
            [bridge_uuid_2],
        )
