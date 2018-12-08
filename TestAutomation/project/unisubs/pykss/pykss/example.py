import re

optional_re = re.compile(r'\[(.*)\]\?')

class Example(object):
    """Represents a single example."""
    def __init__(self, template):
        self.template = template
        self.styles = []

    def add_style(self, name, description, modifier_class):
        if modifier_class:
            html = optional_re.sub(r'\1', self.template)
        else:
            html = optional_re.sub('', self.template)
        html = html.replace('$modifier_class', modifier_class)
        self.styles.append(ExampleStyle(name, description, html))

class ExampleStyle(object):
    """Represents one style of an example.

    Each example will have 1 default style, plus 1 for each of the modifiers.
    """
    def __init__(self, name, description, html):
        self.name = name
        self.description = description
        self.html = html
