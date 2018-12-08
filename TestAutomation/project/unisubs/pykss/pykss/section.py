import re

from pykss.example import Example
from pykss.modifier import Modifier


CLASS_MODIFIER = '.'
PSEUDO_CLASS_MODIFIER = ':'
MODIFIER_DESCRIPTION_SEPARATOR = ' - '
EXAMPLE_START = 'Example:'
REFERENCE_START = 'Styleguide'

reference_re = re.compile(r'%s ([\w\.]+)' % REFERENCE_START)
multiline_modifier_re = re.compile(r'^\s+(\w.*)')


class Section(object):

    def __init__(self, comment=None, filename=None):
        self.comment = comment or ''
        self.filename = filename

    def parse(self):
        self._description_lines = []
        self._modifiers = []
        self._example_lines = []
        self._examples = []
        self._reference = None

        in_example = False
        in_modifiers = False

        for line in self.comment.splitlines():
            if line.startswith(CLASS_MODIFIER) or line.startswith(PSEUDO_CLASS_MODIFIER):
                in_modifiers = True
                try:
                    modifier, description = line.split(MODIFIER_DESCRIPTION_SEPARATOR)
                except ValueError:
                    pass
                else:
                    self._modifiers.append(Modifier(modifier.strip(), description.strip()))

            elif in_modifiers and multiline_modifier_re.match(line):
                match = multiline_modifier_re.match(line)
                if match:
                    description = match.groups()[0]
                    last_modifier = self._modifiers[-1]
                    last_modifier.description += ' {0}'.format(description)

            elif line.startswith(EXAMPLE_START):
                in_example = True
                in_modifiers = False
                self.finish_example()

            elif line.startswith(REFERENCE_START):
                in_example = False
                in_modifiers = False
                match = reference_re.match(line)
                if match:
                    self._reference = match.groups()[0].rstrip('.')

            elif in_example is True:
                self._example_lines.append(line)

            else:
                in_modifiers = False
                self._description_lines.append(line)

        self.finish_example()
        self._description = '\n'.join(self._description_lines).strip()

    @property
    def description(self):
        if not hasattr(self, '_description'):
            self.parse()
        return self._description

    @property
    def modifiers(self):
        if not hasattr(self, '_modifiers'):
            self.parse()
        return self._modifiers

    @property
    def examples(self):
        if not hasattr(self, '_modifiers'):
            self.parse()
        return self._examples

    @property
    def section(self):
        if not hasattr(self, '_reference'):
            self.parse()
        return self._reference

    def finish_example(self):
        """Finish the current example.

        While parsing an example, we build up the _example_lines list.  This
        method takes those lines, creates an Example object from them, then
        clears them out.

        If _example_lines is empty, then this is a no-op.
        """
        if not self._example_lines:
            return
        example = Example('\n'.join(self._example_lines).strip())
        # Add default style
        example.add_style(None, None, '')
        for modifier in self._modifiers:
            example.add_style(modifier.name, modifier.description,
                              modifier.class_name)
        self._examples.append(example)
        self._example_lines = []
