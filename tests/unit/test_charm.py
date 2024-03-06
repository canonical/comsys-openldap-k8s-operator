# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm unit tests."""

# pylint:disable=protected-access

import json
import logging
from unittest import TestCase, mock

from ops.model import ActiveStatus, BlockedStatus
from ops.pebble import CheckStatus
from ops.testing import Harness

from charm import OpenLDAPK8SCharm
from state import State

logger = logging.getLogger(__name__)


class TestCharm(TestCase):
    """Unit tests.

    Attrs:
        maxDiff: Specifies max difference shown by failed tests.
    """

    maxDiff = None

    def setUp(self):
        """Set up for the unit tests."""
        self.harness = Harness(OpenLDAPK8SCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_can_connect("openldap", True)
        self.harness.set_leader(True)
        self.harness.set_model_name("openldap-model")
        self.harness.add_network("10.0.0.10", endpoint="peer")
        self.harness.begin()
        logging.info("setup complete")

    def test_initial_plan(self):
        """The initial pebble plan is empty."""
        harness = self.harness
        initial_plan = harness.get_container_pebble_plan("openldap").to_dict()
        self.assertEqual(initial_plan, {})

    def test_waiting_on_peer_relation_not_ready(self):
        """The charm is blocked without a peer relation."""
        harness = self.harness

        # Simulate pebble readiness.
        container = harness.model.unit.get_container("openldap")
        harness.charm.on.openldap_pebble_ready.emit(container)

        # No plans are set yet.
        got_plan = harness.get_container_pebble_plan("openldap").to_dict()
        self.assertEqual(got_plan, {})

        # The BlockStatus is set with a message.
        self.assertEqual(
            harness.model.unit.status,
            BlockedStatus("peer relation not ready"),
        )

    def test_pebble_plan_ready(self):
        """The pebble plan is correctly generated when the charm is ready."""
        harness = self.harness
        simulate_lifecycle(harness)

        # The plan is generated after pebble is ready.
        want_plan = {
            "services": {
                "openldap": {
                    "override": "replace",
                    "summary": "openldap",
                    "startup": "enabled",
                    "command": "/container/tool/run",
                    "environment": {
                        "CHARM_DEPLOYMENT_NAME": "comsys-openldap-k8s",
                        "LDAP_ADMIN_PASSWORD": "admin",
                        "LDAP_ADMIN_USERNAME": "admin",
                        "LDAP_BASE_DN": "dc=canonical,dc=dev,dc=com",
                        "LDAP_DOMAIN": "canonical.dev.com",
                        "LDAP_LOG_LEVEL": "256",
                        "LDAP_ORGANISATION": "Canonical",
                        "LDAP_TLS": "false",
                    },
                }
            },
        }
        got_plan = harness.get_container_pebble_plan("openldap").to_dict()
        got_plan["services"]["openldap"]["environment"][
            "LDAP_ADMIN_PASSWORD"
        ] = "admin"  # nosec
        self.assertEqual(got_plan["services"], want_plan["services"])

        # The service was started.
        service = harness.model.unit.get_container("openldap").get_service(
            "openldap"
        )
        self.assertTrue(service.is_running())

        # The MaintenanceStatus is set with replan message.
        self.assertEqual(
            harness.model.unit.status,
            ActiveStatus(),
        )

    def test_config_changed(self):
        """The pebble plan changes according to config changes."""
        harness = self.harness
        simulate_lifecycle(harness)

        # Update the config.
        self.harness.update_config({"ldap-base-dn": "dc=foo,dc=com"})

        # The new plan reflects the change.
        want_base_dn = "dc=foo,dc=com"
        got_base_dn = harness.get_container_pebble_plan("openldap").to_dict()[
            "services"
        ]["openldap"]["environment"]["LDAP_BASE_DN"]

        self.assertEqual(got_base_dn, want_base_dn)

        # The ActiveStatus is set with replan message.
        self.assertEqual(
            harness.model.unit.status,
            ActiveStatus(),
        )

    def test_update_status_up(self):
        """The charm updates the unit status to active based on UP status."""
        harness = self.harness

        simulate_lifecycle(harness)

        container = harness.model.unit.get_container("openldap")
        container.get_check = mock.Mock(status="up")
        container.get_check.return_value.status = CheckStatus.UP
        harness.charm.on.update_status.emit()

        self.assertEqual(
            harness.model.unit.status, ActiveStatus()
        )

    def test_update_relation_data(self):
        """Test the relation provider."""
        harness = self.harness
        simulate_lifecycle(harness)

        rel_id = harness.add_relation("ldap", "ranger-usersync-k8s")
        harness.add_relation_unit(rel_id, "ranger-usersync-k8s/0")

        event = make_ldap_relation_changed_event(rel_id)
        harness.charm.provider._on_relation_changed(event)

        relation_data = self.harness.get_relation_data(
            rel_id, "comsys-openldap-k8s"
        )
        assert relation_data["admin_password"]
        assert relation_data["base_dn"]


def simulate_lifecycle(harness):
    """Simulate a healthy charm life-cycle.

    Args:
        harness: ops.testing.Harness object used to simulate charm lifecycle.
    """
    # Simulate peer relation readiness.
    harness.add_relation("peer", "openldap")

    # Simulate pebble readiness.
    container = harness.model.unit.get_container("openldap")
    harness.charm.on.openldap_pebble_ready.emit(container)


def make_ldap_relation_changed_event(rel_id):
    """Create and return a mock relation changed event.

    The event is generated by the relation with ranger-usersync-k8s.

    Args:
        rel_id: the relation id.

    Returns:
        Event dict.
    """
    return type(
        "Event",
        (),
        {
            "app": "ranger-usersync-k8s",
            "relation": type(
                "Relation",
                (),
                {
                    "data": {
                        "ranger-usersync-k8s": {
                            "user": "admin",
                        }
                    },
                    "id": rel_id,
                },
            ),
        },
    )


class TestState(TestCase):
    """Unit tests for state.

    Attrs:
        maxDiff: Specifies max difference shown by failed tests.
    """

    maxDiff = None

    def test_get(self):
        """It is possible to retrieve attributes from the state."""
        state = make_state({"foo": json.dumps("bar")})
        self.assertEqual(state.foo, "bar")
        self.assertIsNone(state.bad)

    def test_set(self):
        """It is possible to set attributes in the state."""
        data = {"foo": json.dumps("bar")}
        state = make_state(data)
        state.foo = 42
        state.list = [1, 2, 3]
        self.assertEqual(state.foo, 42)
        self.assertEqual(state.list, [1, 2, 3])
        self.assertEqual(data, {"foo": "42", "list": "[1, 2, 3]"})

    def test_del(self):
        """It is possible to unset attributes in the state."""
        data = {"foo": json.dumps("bar"), "answer": json.dumps(42)}
        state = make_state(data)
        del state.foo
        self.assertIsNone(state.foo)
        self.assertEqual(data, {"answer": "42"})
        # Deleting a name that is not set does not error.
        del state.foo

    def test_is_ready(self):
        """The state is not ready when it is not possible to get relations."""
        state = make_state({})
        self.assertTrue(state.is_ready())

        state = State("myapp", lambda: None)
        self.assertFalse(state.is_ready())


def make_state(data):
    """Create state object.

    Args:
        data: Data to be included in state.

    Returns:
        State object with data.
    """
    app = "myapp"
    rel = type("Rel", (), {"data": {app: data}})()
    return State(app, lambda: rel)
