"""
command -- Implement the CLI command/subcommand pattern

This module makes it easy to implement the CLI command/subcommand pattern used
by lots of modern CLI programs (git, hg, docker, etc).  Using this module you
can create a mega-command that's composed of of smaller/interrelated,
utilities (for example: git fetch, git checkout, git push, etc).

To use this module:
  - Create a bunch of Command subclasses for your functionality
  - Create a RootCommand class set your command instances as its
    subcommands
  - You can also add CompositeCommands as subcommands to create an extra
    level of nesting (for example git stash is composed of stash list, git
    stash pop, etc.)
  - Call execute() on your top-level RootCommand
"""

import argparse
import inspect
import sys

class Command(object):
    """
    Command -- Base class for commands

    Each subclass of this implements a concrete command utility.

      - By default, the name of the command is the name of the class
        lowercased.
      - Implement functionality in the run() method.
      - If you support options/arguments, override add_arguments()
      - Make a docstring with a short description -- this will be used for the
        help text
      - Consider changing usage, epilog, use_long_description and add_help to
        tweak the help text.
    """
    usage = '%(prog)s [options]'
    epilog = None
    add_help = True
    use_long_description = True
    raw_args = False

    def __init__(self):
        self.parent_prog = None

    @classmethod
    def name(cls):
        return cls.__name__.lower()

    @classmethod
    def short_description(cls):
        if cls.__doc__ is None:
            return ''
        return cls.__doc__.strip().split('\n')[0]

    @classmethod
    def long_description(cls):
        if cls.__doc__ is None:
            return ''
        lines = cls.__doc__.split('\n')
        common_leading_space = min(
            len(line) - len(line.lstrip())
            for line in lines
            if line
        )
        return '\n'.join(line[common_leading_space:] for line in lines)

    @classmethod
    def description(cls):
        if cls.use_long_description:
            return cls.long_description()
        else:
            return cls.short_description()

    def prog(self):
        if self.parent_prog:
            return self.parent_prog + ' ' + self.name()
        else:
            return self.name()

    def make_parser(self):
        parser = argparse.ArgumentParser(
            prog=self.prog(),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            usage=self.usage, description=self.description(),
            epilog=self.epilog, add_help=self.add_help)
        self.add_arguments(parser)
        return parser

    def add_arguments(self, parser):
        pass

    def parse_args(self, command_args):
        parser = self.make_parser()
        if self.raw_args:
            self.args = command_args
        else:
            self.args = parser.parse_args(command_args)

    def execute(self, command_args):
        self.parse_args(command_args)
        self.run()

    def run(self):
        """Override this in your subclasses."""
        pass

    def print_help(self):
        self.make_parser().print_help()

class CompositeCommand(Command):
    """
    Command composed of other commands

    Typical usage is to create a new CompositeCommand subclass and set the
    subcommands attribute to a list of Command instances or classes.
    """
    subcommands = []
    usage = "%(prog)s [subcommand]"
    add_help = False

    def __init__(self):
        super().__init__()
        self._subcommands = [
            sc() if inspect.isclass(sc) else sc
            for sc in self.subcommands
        ]

    def get_subcommands(self):
        return self._subcommands

    def description(self):
        parts = [
            super().description()
        ]
        parts.append('\n\nSubcommands:\n')
        for subcommand in self.get_subcommands():
            parts.append('  {:20}{}\n'.format(
                subcommand.name(), subcommand.short_description()))
        parts.append('\n')
        return ''.join(parts)

    def add_arguments(self, parser):
        parser.formatter_class=argparse.RawTextHelpFormatter
        parser.add_argument('subcommand', nargs='?', help=argparse.SUPPRESS)
        parser.add_argument('subcommand_args', nargs=argparse.REMAINDER,
                            help=argparse.SUPPRESS)

    def get_subcommand(self, name):
        for subcommand in self.get_subcommands():
            if subcommand.name() == name:
                return subcommand
        raise LookupError(name)

    def run(self):
        subcommand_name = self.args.subcommand
        if subcommand_name is None:
            self.print_help()
        else:
            try:
                subcommand = self.get_subcommand(subcommand_name)
            except LookupError:
                self.print_help()
            else:
                subcommand.execute(self.args.subcommand_args)

class RootCommand(CompositeCommand):
    """
    Root CompositeCommand

    Root command is a CompositeCommand that adds:
        - The help subcommand
        - The main() helper method
    """
    def __init__(self):
        super().__init__()
        self.help_command = Help(self)
        self.help_command.parent_prog = self.prog()

    def get_subcommands(self):
        return super().get_subcommands() + [self.help_command]

    def main(self):
        """
        Main entrypoint

        This method makes it easy to execute a command from the main script.
        """
        parser = self.make_parser()
        self.execute(sys.argv[1:])

class Help(Command):
    """Get help on a command"""
    usage = "%(prog)s [command]"
    add_help = False

    def __init__(self, root_command):
        super().__init__()
        self.root_command = root_command

    def add_arguments(self, parser):
        parser.add_argument('subcommand', nargs='*', help=argparse.SUPPRESS)

    def lookup_subcommand(self):
        subcommand_names = self.args.subcommand
        current_command = self.root_command
        for name in subcommand_names:
            current_command = current_command.get_subcommand(name)
        return current_command

    def run(self):
        if self.args.subcommand:
            try:
                subcommand = self.lookup_subcommand()
                subcommand.print_help()
            except LookupError:
                print('Invalid command: {}'.format(
                    ' '.join(self.args.subcommand)))
        else:
            self.print_help()
