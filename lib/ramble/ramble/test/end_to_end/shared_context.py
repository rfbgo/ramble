# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import glob
import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mock_applications",
    "mock_modifiers",
)

workspace = RambleCommand("workspace")


def test_shared_contexts(
    mutable_config,
    mutable_mock_workspace_path,
    mock_applications,
    mock_modifiers,
    workspace_name,
):
    global_args = ["-w", workspace_name]
    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            "shared-context",
            "--wf",
            "test_wl",
            "-e",
            "simple_test",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-v",
            "modeless_required_var=1",
            global_args=global_args,
        )
        workspace(
            "manage",
            "modifiers",
            "--add",
            "-n",
            "test-mod",
            "-s",
            "shared-context:test_wl:simple_test",
            global_args=global_args,
        )
        ws._re_read()

        workspace("setup", "--dry-run", global_args=global_args)

        # Create fake figures of merit.
        exp_dir = os.path.join(ws.root, "experiments", "shared-context", "test_wl", "simple_test")
        with open(os.path.join(exp_dir, "simple_test.out"), "w+", encoding="utf-8") as f:
            f.write("fom_context mod_context\n")
            f.write("123.4 seconds app_fom\n")

        with open(os.path.join(exp_dir, "test_analysis.log"), "w+", encoding="utf-8") as f:
            f.write("fom_contextFOM_GOES_HERE")

        workspace("analyze", "-f", "text", "json", global_args=["-w", workspace_name])

        results_files = glob.glob(os.path.join(ws.results_dir, "results.latest.txt"))

        with open(results_files[0], encoding="utf-8") as f:
            data = f.read()
            assert "matched_shared_context" in data  # find the merged context
            assert "test_fom = 123.4" in data  # from the app
            assert "shared_context_fom" in data  # from the mod
