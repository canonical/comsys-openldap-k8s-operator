#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm the service."""

import logging

import ops
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus
from ops.pebble import ExecError

from literals import APPLICATION_PORT
from relations.provider import LDAPProvider
from state import State
from utils import log_event_handler, random_string

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class OpenLDAPK8SCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        """Construct.

        Args:
            args: Ignore.
        """
        super().__init__(*args)
        self._state = State(self.app, lambda: self.model.get_relation("peer"))
        self.name = "openldap"

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(
            self.on.openldap_pebble_ready, self._on_openldap_pebble_ready
        )
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.restart_action, self._on_restart)
        self.framework.observe(
            self.on.get_admin_password_action, self._on_get_admin_password
        )
        self.framework.observe(
            self.on.load_test_users_action, self._on_load_test_users
        )
        self.provider = LDAPProvider(self)

    @log_event_handler(logger)
    def _on_install(self, event):
        """Install application.

        Args:
            event: The event triggered when the relation changed.
        """
        self.unit.status = MaintenanceStatus("installing OpenLdap")

    @log_event_handler(logger)
    def _on_openldap_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Define and start openldap using the Pebble API.

        Args:
            event: The event triggered when the relation changed.
        """
        self.update(event)

    @log_event_handler(logger)
    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle configuration changes.

        Args:
            event: The event triggered when the relation changed.
        """
        self.update(event)

    @log_event_handler(logger)
    def _on_load_test_users(self, event):
        """Handle loading of test users and groups.

        Args:
            event: The `load-test-users` action event.

        Raises:
            ExecError: In case of error during keytool certificate import
        """
        self.unit.status = MaintenanceStatus("Running action.")
        container = self.unit.get_container(self.name)
        if not container.can_connect():
            event.defer()
            return

        admin_pwd = self._state.bind_password
        base_dn = self._state.base_dn

        command = [
            "ldapadd",
            "-x",
            "-H",
            "ldap://localhost:389",
            "-D",
            f"cn=admin,{base_dn}",
            "-w",
            admin_pwd,
            "-f",
            "startup.ldif",
            "-v",
        ]

        try:
            container.exec(
                command, working_dir="/templates", service_context="openldap"
            ).wait_output()
            event.set_results(
                {"result": "test users and groups successfully added"}
            )
            self.unit.status = ActiveStatus()
        except ExecError as e:
            logger.error(e.stdout)
            raise

    def _on_restart(self, event):
        """Restart application, action handler.

        Args:
            event:The event triggered by the restart action
        """
        container = self.unit.get_container(self.name)
        if not container.can_connect():
            event.defer()
            return

        self.unit.status = MaintenanceStatus("restarting openldap")
        container.restart(self.name)
        event.set_results({"result": "openldap successfully restarted"})
        self.unit.status = ActiveStatus()

    def _on_get_admin_password(self, event):
        """Get admin password, action handler.

        Args:
            event:The event triggered by the `get-admin-password` action.
        """
        admin_password = self._state.bind_password
        event.set_results({"admin-password": admin_password})

    def validate(self):
        """Validate that configuration and relations are valid and ready.

        Raises:
            ValueError: in case of invalid configuration.
        """
        if not self._state.is_ready():
            raise ValueError("peer relation not ready")

    def update(self, event):
        """Update the openldap server configuration and re-plan its execution.

        Args:
            event: The event triggered when the relation changed.
        """
        try:
            self.validate()
        except ValueError as err:
            self.unit.status = BlockedStatus(str(err))
            return

        container = self.unit.get_container(self.name)
        if not container.can_connect():
            event.defer()
            return

        container.push_path("templates/", "/")
        self.model.unit.open_port(port=APPLICATION_PORT, protocol="tcp")

        logger.info("configuring openldap")

        context = {}
        for key, value in self.config.items():
            updated_key = key.upper().replace("-", "_")
            context[updated_key] = value

        # Set provider values in state
        self._state.bind_password = self._state.bind_password or random_string(
            12
        )
        self._state.base_dn = self.config["ldap-base-dn"]

        context.update(
            {
                "LDAP_ADMIN_PASSWORD": self._state.bind_password,
                "LDAP_ADMIN_USERNAME": "admin",
                "LDAP_TLS": "false",
            }
        )

        logger.info("planning openldap execution")
        pebble_layer = {
            "summary": "openldap layer",
            "services": {
                self.name: {
                    "summary": "openldap",
                    "command": "/container/tool/run",
                    "startup": "enabled",
                    "override": "replace",
                    "environment": context,
                }
            },
        }
        container.add_layer(self.name, pebble_layer, combine=True)
        container.replan()

        self.unit.status = ActiveStatus("Status check: UP")


if __name__ == "__main__":  # pragma: nocover
    ops.main(OpenLDAPK8SCharm)
