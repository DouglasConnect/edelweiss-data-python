#!/usr/bin/env python3

import re
import inspect
from docstring_parser import parse

import edelweiss_data.api as api

# short_description
# blank_after_short_description
# long_description
# blank_after_long_description
# meta
# raises
# returns
#   description
#   is_generator
#   type_name
# params
#   arg_name
#   args
#   default
#   description
#   is_optional
#   type_name


def main():
    readme = load_readme("README.md")
    m = re.search(r'(?P<before_api_reference>.*?\n# API reference)', readme, re.DOTALL)
    save_readme("README.md", m.group('before_api_reference') + "\n\n" + get_api_docs(api))


def load_readme(filename):
    with open(filename, "r") as fi:
        return fi.read()


def save_readme(filename, content):
    with open(filename, "w") as fo:
        fo.write(content)


def get_api_docs(module):

    def join_items(gen):
        string = "\n\n".join([x for x in gen if x is not None])
        return re.sub(r'\n{2,}', '\n\n', string)

    def aux(obj, level=1):
        for name, obj in inspect.getmembers(obj):
            if (inspect.isclass(obj) or inspect.isfunction(obj) or inspect.ismethod(obj)) and not re.match(r'^__.+__$', name) and not re.match(r'^_.+', name):
                yield join_items(parse_docs(name, obj, level))
                yield join_items(aux(obj, level + 1))
    return join_items(aux(module))


def parse_docs(name, obj, level=1):
    doc = inspect.getdoc(obj)
    docstring = parse(doc)
    yield "#" * (level + 1) + " `{}`".format(name)
    yield docstring.short_description
    yield docstring.long_description
    if docstring.returns is not None:
        yield "*Returns:* %s" % docstring.returns.description
    for param in docstring.params:
        yield "*{}* {}".format(param.arg_name, (" : %s" % param.description) if param.description else "")


if __name__ == "__main__":
    main()
