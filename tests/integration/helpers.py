#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm integration test helpers."""

import logging
from pathlib import Path

import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


APP_NAME = "openldap-k8s"
METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())


async def get_unit_url(
    ops_test: OpsTest, application, unit, port, protocol="http"
):
    """Return unit URL from the model.

    Args:
        ops_test: PyTest object.
        application: Name of the application.
        unit: Number of the unit.
        port: Port number of the URL.
        protocol: Transfer protocol (default: https).

    Returns:
        Unit URL of the form {protocol}://{address}:{port}
    """
    status = await ops_test.model.get_status()  # noqa: F821
    address = status["applications"][application]["units"][
        f"{application}/{unit}"
    ]["address"]
    return f"{protocol}://{address}:{port}"
