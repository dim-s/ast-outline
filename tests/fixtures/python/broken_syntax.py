# Deliberately broken Python — used to verify parse-error counting.
# tree-sitter-python produces ERROR / MISSING nodes for unmatched
# brackets, bad indentation, and incomplete expressions.

def ok():
    return 1


def broken(
    x =
    return x


class Partial
    def method(self):
        pass
