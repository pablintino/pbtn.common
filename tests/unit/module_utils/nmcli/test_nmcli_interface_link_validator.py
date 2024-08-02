import typing

import pytest
from ansible_collections.pbtn.common.plugins.module_utils.net import (
    net_config,
)

from ansible_collections.pbtn.common.plugins.module_utils.nmcli import (
    nmcli_interface_exceptions,
    nmcli_interface_link_validator,
)

from ansible_collections.pbtn.common.tests.unit.module_utils.test_utils import (
    config_stub_data,
    net_config_stub,
)


def test_nmcli_link_validator_validate_mandatory_links_ok(mocker):
    ip_interface_mocker = mocker.Mock()
    ip_interface_mocker.get_ip_links.return_value = config_stub_data.TEST_IP_LINKS
    validator = nmcli_interface_link_validator.NmcliLinkValidator(ip_interface_mocker)
    validator.validate_mandatory_links(
        net_config_stub.build_testing_ether_config(mocker)
    )
    validator.validate_mandatory_links(
        net_config_stub.build_testing_vlan_config(mocker)
    )
    validator.validate_mandatory_links(
        net_config_stub.build_testing_ether_bridge_config(mocker, slaves_count=2)
    )


def test_nmcli_link_validator_validate_mandatory_links_fail(mocker):
    ip_interface_mocker = mocker.Mock()
    ip_interface_mocker.get_ip_links.return_value = config_stub_data.TEST_IP_LINKS
    validator = nmcli_interface_link_validator.NmcliLinkValidator(ip_interface_mocker)

    # Basic test for an ethernet connection
    ether_config = net_config_stub.build_testing_ether_config(mocker, index=100)
    with pytest.raises(
        nmcli_interface_exceptions.NmcliInterfaceValidationException
    ) as err:
        validator.validate_mandatory_links(ether_config)
    assert (
        str(err.value).lower()
        == f"Cannot determine the interface to use for {ether_config.name} connection. "
        f"Interface {ether_config.interface.iface_name} not found".lower()
    )

    # Basic test for a VLAN connection
    vlan_config = net_config_stub.build_testing_vlan_config(mocker, index=100)
    with pytest.raises(
        nmcli_interface_exceptions.NmcliInterfaceValidationException
    ) as err:
        validator.validate_mandatory_links(vlan_config)
    assert (
        str(err.value).lower()
        == f"cannot determine the parent interface to use for {vlan_config.name} connection. "
        f"Interface {vlan_config.parent_interface.iface_name} not found".lower()
    )

    # Basic test for a bridge connection with a failing ethernet slave
    bridge_ether_slaves_config = net_config_stub.build_testing_ether_bridge_config(
        mocker, slaves_count=1, start_index=100
    )
    with pytest.raises(
        nmcli_interface_exceptions.NmcliInterfaceValidationException
    ) as err:
        validator.validate_mandatory_links(bridge_ether_slaves_config)
    assert (
        str(err.value).lower()
        == f"cannot determine the interface to use for {bridge_ether_slaves_config.slaves[0].name} connection. "
        f"Interface {bridge_ether_slaves_config.slaves[0].interface.iface_name} not found".lower()
    )

    # Basic test for a bridge connection with a failing VLAN slave
    bridge_vlan_slaves_config = net_config_stub.build_testing_vlan_bridge_config(
        mocker, slaves_count=1, start_index=100
    )
    slave_conn_config = typing.cast(
        net_config.VlanSlaveConnectionConfig, bridge_vlan_slaves_config.slaves[0]
    )
    with pytest.raises(
        nmcli_interface_exceptions.NmcliInterfaceValidationException
    ) as err:
        validator.validate_mandatory_links(bridge_vlan_slaves_config)
    assert (
        str(err.value).lower()
        == f"cannot determine the parent interface to use for {slave_conn_config.name} connection. "
        f"Interface {slave_conn_config.parent_interface.iface_name} not found".lower()
    )
