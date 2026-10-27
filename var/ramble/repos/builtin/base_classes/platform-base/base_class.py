# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for platform definitions"""

import ramble.repository
from ramble.language.language_base import DirectiveMeta
from ramble.language.shared_language import (
    register_validator,
    required_variable,
    variant,
    when,
)
from ramble.util.naming import NS_SEPARATOR

ObjectMixin = ramble.repository.get_base_class("object-mixin")


class PlatformBase(ObjectMixin, metaclass=DirectiveMeta):
    name = None
    origin_type = "platform"
    _builtin_name = NS_SEPARATOR.join(
        ("platform_builtin", "{obj_name}", "{name}")
    )
    _language_types = ["platform", "shared"]

    variant(
        "accelerator",
        default=False,
        description="Whether platform has accelerator or not",
    )

    variant(
        "accelerator_type",
        default=None,
        values=[None],
        description="Type of accelerator on this platform",
    )

    variant(
        "validate_platform",
        default=True,
        description="Whether to validate the platform configuration",
    )

    with when("+validate_platform"):
        required_variable(
            "max_accelerators_per_node",
            description="Maximum number of accelerators per node for this platform",
        )

        required_variable(
            "max_sockets_per_node",
            description="Maximum number of sockets per node on this platform",
        )

        required_variable(
            "max_threads_per_core",
            description="Maximum number of threads per core for this platform",
        )

        required_variable(
            "max_cores_per_node",
            description="Maximum number of cores per node for this platform",
        )

        required_variable(
            "max_memory_per_node",
            description="Maximum amount of memory per node for this platform",
        )

        register_validator(
            "threads_per_node_platform_validation",
            predicate="{n_threads} * {processes_per_node} <= {max_cores_per_node}",
            message="Number of threads per node ({n_threads} * {processes_per_node}) "
            "exceeds max cores per node ({max_cores_per_node})",
        )

        register_validator(
            "accelerators_per_node_platform_validation",
            predicate="{accelerators_per_node} <= {max_accelerators_per_node}",
            message="Number of accelerators per node ({accelerators_per_node}) "
            "exceeds max accelerators on node ({max_accelerators_per_node})",
        )
