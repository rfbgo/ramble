# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""
Spack environments house software stacks.

This module contains classes and methods that will help manage a spack
environment by calling an externally available spack.
"""

import os
import re

import llnl.util.tty as tty
import llnl.util.filesystem as fs
from spack.util.executable import which, CommandNotFoundError, ProcessError
import spack.util.spack_yaml as syaml

import ramble.error

spack_namespace = 'spack'


class SpackRunner(object):
    """Runner for executing several spack commands

    The SpackRunner class is primarily used to manage spack environments
    for executing experiments under.

    This calss provides methods for creating and manaving spack environments,
    and for ensuring required compilers are installed. It also provides a
    method for generating variables that can be used to ensure a spack env
    is loaded within an execution script.
    """
    env_key = 'SPACK_ENV'

    env_create_args = [
        'env',
        'create',
        '-d',
        '.'
    ]

    compiler_find_args = ['compiler', 'find']

    def __init__(self, shell='bash', dry_run=False):
        """
        Ensure spack is found in the path, and setup some default variables.
        """
        try:
            self.exe = which('spack', required=True)
        except CommandNotFoundError:
            raise RunnerError("Spack command is not found in path")

        self.spack_dir = os.path.dirname(os.path.dirname(self.exe.exe[0]))
        self.shell = shell

        if self.shell == 'bash':
            script = 'setup-env.sh'
        elif self.shell == 'csh':
            script = 'setup-env.csh'
        elif self.shell == 'fish':
            script = 'setup-env.fish'
        self.source_script = os.path.join(self.spack_dir,
                                          'share', 'spack', script)

        self.env_path = None
        self.active = False
        self.compilers = []
        self.dry_run = dry_run

    def generate_expand_vars(self, expander, specs=[], shell='bash'):
        """
        Generate a string to load a spack environment within a generated
        script.
        """

        commands = ['source %s' % self.source_script]

        if self.active:
            commands.append('spack env activate %s' % self.env_path)

        commands.append('source %s/loads' % self.env_path)

        return '\n'.join(commands)

    def create_env(self, path, output=None, error=None):
        """
        Ensure a spack environment is created, and set the path to it within
        this runner.
        """
        if os.path.exists(path) and not os.path.isdir(path):
            raise RunnerError('Unable to create environment %s' % path)

        if not os.path.exists(path):
            fs.mkdirp(path)

        # Create a spack env
        if not os.path.exists(os.path.join(path, 'spack.yaml')):
            with fs.working_dir(path):
                self.exe(*self.env_create_args)

        # Ensure subsequent commands use the created env now.
        self.env_path = path

    def load_compiler(self, spec):
        """
        Add commands to load a package to the executable
        """
        if self.shell == 'bash':
            regex = \
                re.compile('\A.*export ' +  # noqa: W605
                           '(?P<var>[\S^=]+)=' +  # noqa: W605
                           '(?P<val>[\S]+);\Z')  # noqa: W605

            shell_flag = '--sh'
        elif self.shell == 'csh':
            regex = \
                re.compile('\A.*setenv ' +  # noqa: W605
                           '(?P<var>[\S^=]+) ' +  # noqa: W605
                           '(?P<val>[\S]+);\Z')  # noqa: W605
            shell_flag = '--csh'
        elif self.shell == 'fish':
            regex = \
                re.compile('\A.*set -gx ' +  # noqa: W605
                           '(?P<var>[\S^=]+) ' +  # noqa: W605
                           '(?P<val>[\S]+);\Z')  # noqa: W605
            shell_flag = '--fish'
        else:
            raise RunnerError('Shell %s not supported' % self.shell)

        self._load_compiler_shell(spec, shell_flag, regex)

    def _load_compiler_shell(self, spec, shell_flag, regex):
        args = [
            'load',
            shell_flag,
            spec
        ]

        if not self.dry_run:
            load_cmds = self.exe(*args, output=str).split('\n')

            for cmd in load_cmds:
                env_var = regex.match(cmd)
                if env_var:
                    self.exe.add_default_env(env_var.group('var'),
                                             env_var.group('val'))
        else:
            self._dry_run_print(args)

    def install_compiler(self, spec):
        """
        Ensure a compiler is installed, before using it to install packages
        within an environment.

        This command always executes outside of an environment.

        If it is executed within an environment, then it adds the compiler to
        the list of environment specs. This can cause conflicts if an
        incompatible package is explicitly added to the environment later.

        Also, if it is added to an environment, sometimes it will cause a
        compiler to be installed multiple times with different base compilers.
        """
        active_env = None
        if self.active:
            active_env = self.exe.default_env[self.env_key]
            del self.exe.default_env[self.env_key]

        find_args = [
            'find',
            spec
        ]

        try:
            self.exe(*find_args, output=os.devnull, error=os.devnull)
            tty.debug('%s is already an installed compiler' % spec)
        except ProcessError:
            args = [
                'install',
                '--reuse',
                spec
            ]

            if not self.dry_run:
                self.exe(*args)
            else:
                self._dry_run_print(args)

        self.load_compiler(spec)

        if not self.dry_run:
            self.exe(*self.compiler_find_args)

            self.compilers.append(spec)

            if self.active:
                self.exe.add_default_env(self.env_key, active_env)
        else:
            self._dry_run_print(self.compiler_find_args)

    def add_compiler(self, spec):
        """Add a compiler to an environment.
        """
        self._check_active()

        if spec not in self.env_contents:
            self.env_contents.append(spec)

    def activate(self):
        """
        Ensure the spack environment is active in subsequent commands.
        """
        if not self.env_path:
            raise NoPathRunnerError('Environment runner has no ' +
                                    'path congfigured')

        self.exe.add_default_env(self.env_key, self.env_path)

        self.env_contents = self.compilers.copy()

        self.active = True

    def deactivate(self):
        """
        Ensure the spack environment is not active in subsequent commands.
        """
        if not self.env_path:
            raise NoPathRunnerError('Environment runner has no ' +
                                    'path congfigured')

        if self.active and self.env_key in self.exe.default_env.keys():
            del self.exe.default_env[self.env_key]
            self.active = False

    def _check_active(self):
        if not self.env_path:
            raise NoPathRunnerError('Environment runner has no ' +
                                    'path congfigured')

        if not self.active:
            raise NoActiveEnvironmentError('Runner has no active ' +
                                           'environment to work with.')

    def add_spec(self, spec):
        """
        Add a spec to the spack environment.

        This command requires an active spack environment.
        """
        self._check_active()

        if spec not in self.env_contents:
            self.env_contents.append(spec)

    def concretize(self):
        """
        Concretize a spack environment.

        This happens by generating a spack.yaml file to build
        the packages that should be in the environment.

        This command requires an active spack environment.
        """
        self._check_active()

        env_file = {}
        env_file[spack_namespace] = {}
        env_file[spack_namespace]['concretizer'] = {}
        env_file[spack_namespace]['concretizer']['unify'] = True

        env_file[spack_namespace]['specs'] = []
        env_file[spack_namespace]['specs'].extend(self.env_contents)

        # Write spack.yaml to environment before concretizing
        with open(os.path.join(self.env_path, 'spack.yaml'), 'w+') as f:
            syaml.dump_config(env_file, f, default_flow_style=False)

        args = [
            'concretize',
            '--reuse'
        ]
        if not self.dry_run:
            self.exe(*args)
        else:
            self._dry_run_print(args)

    def install(self):
        """
        Install spack packages that have been added to an environment.

        This command requires an active spack environment.
        """
        self._check_active()

        args = [
            'install',
            '--reuse'
        ]
        if not self.dry_run:
            self.exe(*args)
        else:
            self._dry_run_print(args)

        for mod_type in ['tcl', 'lmod']:
            args = [
                'module',
                mod_type,
                'refresh',
                '-y'
            ]

            if not self.dry_run:
                self.exe(*args)
            else:
                self._dry_run_print(args)

        args = [
            'env',
            'loads'
        ]
        if not self.dry_run:
            self.exe(*args)
        else:
            self._dry_run_print(args)

    def get_package_path(self, package_spec):
        """Return the installation directory for a package"""
        args = ['location', '-i']
        args.extend(package_spec.split())

        if not self.dry_run:
            return self.exe(*args, output=str).strip()
        else:
            self._dry_run_print(args)
            return '/dry-run/path/to/%s' % package_spec.split()[0]

    def _dry_run_print(self, args):
        tty.msg('DRY-RUN: would run %s' % self.exe.command)
        tty.msg('         with args: %s' % args)


class RunnerError(ramble.error.RambleError):
    """Raised when a problem occurs with a spack environment"""


class NoPathRunnerError(ramble.error.RambleError):
    """Raised when a runner is used that does not have a path set"""


class NoActiveEnvironmentError(RunnerError):
    """Raised when an environment command is executed without an active
    environment."""
