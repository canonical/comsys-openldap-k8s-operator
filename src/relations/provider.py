# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""OpenLDAP client relation hooks & helpers."""


import logging

from ops.charm import CharmBase
from ops.framework import Object
from ops.model import ActiveStatus, MaintenanceStatus

from literals import APPLICATION_PORT
from utils import log_event_handler

logger = logging.getLogger(__name__)


class LDAPProvider(Object):
    """Defines functionality for the 'provides' side of the 'ranger-client' relation.

    Hook events observed:
        - relation-updated
        - relation-broken
    """

    def __init__(self, charm: CharmBase, relation_name: str = "ldap") -> None:
        """Construct LDAPProvider object.

        Args:
            charm: the charm for which this relation is provided
            relation_name: the name of the relation
        """
        self.relation_name = relation_name

        super().__init__(charm, self.relation_name)
        self.framework.observe(
            charm.on[self.relation_name].relation_changed,
            self._on_relation_changed,
        )
        self.framework.observe(
            charm.on[self.relation_name].relation_broken,
            self._on_relation_broken,
        )
        self.charm = charm

    @log_event_handler(logger)
    def _on_relation_changed(self, event):
        """Handle ldap relation changed event.

        Provide related application with bind_dn and admin password.

        Args:
            event: relation changed event.
        """
        if not self.charm.unit.is_leader():
            return

        data = event.relation.data[event.app]

        if not data:
            return

        self.charm.unit.status = MaintenanceStatus("Managing ldap relation")

        self._set_relation_data(event)
        self.charm.unit.status = ActiveStatus()

    def _set_relation_data(self, event):
        """Set the LDAP url, admin_password and bind_dn in the relation databag.

        Args:
            event: relation event
        """
        relation = self.charm.model.get_relation(
            self.relation_name, event.relation.id
        )
        host = self.charm.config["charm-deployment-name"]

        if relation:
            relation.data[self.charm.app].update(
                {
                    "ldap_url": f"ldap://{host}:{APPLICATION_PORT}",
                    "base_dn": self.charm._state.base_dn,
                    "admin_password": self.charm._state.bind_password,
                }
            )

    @log_event_handler(logger)
    def _on_relation_broken(self, event):
        """Handle on relation broken event.

        Args:
            event: on relation broken event.
        """
        if not self.charm.unit.is_leader():
            return

        logger.info("LDAP relation removed.")
