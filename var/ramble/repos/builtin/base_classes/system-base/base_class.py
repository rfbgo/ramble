# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for system definitions"""

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


class SystemBase(ObjectMixin, metaclass=DirectiveMeta):
    name = None
    origin_type = "system"
    _builtin_name = NS_SEPARATOR.join(
        ("system_builtin", "{obj_name}", "{name}")
    )
    _language_types = ["system", "shared"]

    variant(
        "validate_system",
        default=True,
        description="Whether to validate the system configuration",
    )

    with when("+validate_system"):
        required_variable(
            "max_nodes",
            description="Maximum number of nodes available in this system for this platform",
        )

        register_validator(
            "n_nodes_system_validation",
            predicate="{n_nodes} <= {max_nodes}",
            message="Number of nodes requested ({n_nodes}) exceeds max nodes ({max_nodes})",
        )

        register_validator(
            "n_ranks_system_validation",
            predicate="{n_ranks} <= {max_cores_per_node} * {n_nodes}",
            message="Total number of ranks ({n_ranks}) exceeds max cores ({max_cores_per_node} * {n_nodes})",
        )
