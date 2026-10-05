# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
from ramble.error import RambleCommandError
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

config = RambleCommand("config")
workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "configured_shell,expect_error",
    [
        ("csh", True),
        ("bash", False),
    ],
)
def test_target_shells_directive(configured_shell, expect_error):
    ws_name = f"test_{configured_shell}"
    global_args = ["-w", ws_name]
    ws = ramble.workspace.create(ws_name)
    workspace(
        "manage",
        "experiments",
        "hostname",
        "--wf",
        "local",
        "-e",
        "test",
        "-v",
        "n_ranks=1",
        "-v",
        "processes_per_node=1",
        global_args=global_args,
    )
    # This requires bash shell
    workspace("manage", "modifiers", "--add", "-n", "wait-for-bg-jobs", global_args=global_args)
    config("add", f"config:shell:{configured_shell}", global_args=global_args)

    ws._re_read()

    if expect_error:
        with pytest.raises(RambleCommandError):
            workspace("setup", "--dry-run", global_args=global_args)
    else:
        workspace("setup", "--dry-run", global_args=global_args)
