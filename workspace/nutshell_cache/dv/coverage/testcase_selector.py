"""Canonical selectors for pytest node IDs used in coverage evidence."""


def testcase_selector(value):
    """Return a stable module-qualified selector, excluding parametrization.

    A plan entry such as ``tests/full_system/test_axi.py::test_read`` matches
    ``tests/full_system/test_axi.py::test_read[seed-7]`` but cannot accidentally
    match a same-named test from another module. Bare names remain supported
    only for unit fixtures and are not accepted by the production evidence
    audit.
    """
    value = str(value).replace("\\", "/").removeprefix("./")
    if "::" not in value:
        return value.split("[", 1)[0]
    path, node = value.split("::", 1)
    return f"{path}::{node.split('[', 1)[0]}"


testcase_selector.__test__ = False
