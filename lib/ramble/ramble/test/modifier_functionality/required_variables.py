# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.experiment_set
import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "test_name,mode,expect_error",
    [
        (
            "standard_require_hostlist",
            "standard",
            ramble.experiment_set.RambleVariableDefinitionError,
        ),
        ("local_no_require_hostlist", "local", None),
    ],
)
def test_required_variables(
    test_name, mode, expect_error, mutable_mock_workspace_path, mutable_applications
):
    workspace_name = test_name
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            "hostname",
            "--wf",
            "local",
            "-e",
            "test",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )
        workspace(
            "manage",
            "modifiers",
            "--add",
            "-n",
            "gcp-metadata",
            "-m",
            mode,
            global_args=global_args,
        )

        ws._re_read()

        if expect_error:
            with pytest.raises(expect_error):
                workspace("setup", "--dry-run", global_args=global_args)
        else:
            workspace("setup", "--dry-run", global_args=global_args)
