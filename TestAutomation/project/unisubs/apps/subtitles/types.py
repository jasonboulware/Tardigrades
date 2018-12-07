from babelsubs import ParserList, GeneratorList

class SubtitleFormat(object):
    def __init__(self, parser, generator, for_staff=False):
        if parser.file_type != generator.file_type:
            raise ValueError("Parser and Generator do not match")
        self.parser = parser
        self.generator = generator
        self.for_staff = for_staff


class SubtitleFormatListClass(dict):
    def register(self, format):
        file_type = format.parser.file_type

        if isinstance(file_type, list):
            for ft in file_type:
                self[ft.lower()] = format
        else:
            self[file_type] = format

    def __getitem__(self, item):
        return super(SubtitleFormatListClass, self).__getitem__(item.lower())
    
    def __init__(self, parsers, generators, for_staff=False):
        super(SubtitleFormatListClass, self).__init__(self)
        for file_type in list(set(parsers.keys()).intersection(set(generators.keys()))):
            self.register(SubtitleFormat(parsers[file_type], generators[file_type], for_staff=for_staff))
    def for_staff(self):
        return [f for f, val in self.items() if val.for_staff]
SubtitleFormatList = SubtitleFormatListClass(ParserList, GeneratorList, for_staff=False)
