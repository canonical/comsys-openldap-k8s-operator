#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm integration tests."""
import logging

import pytest
from conftest import deploy  # noqa: F401, pylint: disable=W0611
from helpers import APP_NAME
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
@pytest.mark.usefixtures("deploy")
class TestDeployment:
    """Integration tests for OpenLDAP charm."""

    async def test_add_users_action(self, ops_test: OpsTest):
        """Load test users action.

        Args:
            ops_test: PyTest object.
        """
        action = (
            await ops_test.model.applications[APP_NAME]
            .units[0]
            .run_action("load-test-users")
        )
        await action.wait()
        assert (
            ops_test.model.applications[APP_NAME].units[0].workload_status
            == "active"
        )
