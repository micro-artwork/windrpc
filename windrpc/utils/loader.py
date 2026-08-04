import yaml
import os


class LineNumberLoader(yaml.SafeLoader):
    """Custom YAML loader that attaches line numbers to parsed dictionaries."""

    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        mapping['__line__'] = node.start_mark.line + 1
        return mapping
