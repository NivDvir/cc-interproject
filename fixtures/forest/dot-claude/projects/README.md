This directory name (`-Users-alice-projects-demo-fixtures-forest-alpha`) is
the forward encoding of a placeholder absolute path for `fixtures/forest/alpha`, per
`paths.encode_project_dir` (every `/` and `.` replaced by `-`). When a test copies
`fixtures/forest/` into a temporary HOME, `alpha`'s absolute path changes, so this encoded name no
longer matches it. `conftest.py` must re-encode `<temp_home>/forest/alpha` itself (calling the same
forward-encoding logic the installer uses) and rename or look up this directory under the freshly
computed name rather than assuming the name checked into this fixture still applies.
