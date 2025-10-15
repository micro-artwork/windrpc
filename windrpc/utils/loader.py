import yaml
import os


class LineNumberLoader(yaml.SafeLoader):
    """YAML 로더를 커스터마이즈하여 딕셔너리에 줄 번호를 첨부합니다."""

    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        mapping['__line__'] = node.start_mark.line + 1
        return mapping
