# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


from ramble.modkit import *


class DisabledModifier(ModifierBase):
    """Specialized class for disabled modifiers.

    This class can be used to create a disabled modifier from an active
    modifier instance.
    """

    modifier_class = "DisabledModifier"

    disabled = True

    name = "disabled"

    modifier_conflict(None)

    def __init__(self, target):
        if isinstance(target, ModifierBase):
            super().__init__(target._file_path)

            self.name = target.name
            self.maintainers = target.maintainers.copy()
            self.tags = target.tags.copy()
        else:
            super().__init__(target)

    def define_variable(self, var_name, var_value):
        """Given this modifier is disabled, never define variables in it"""
