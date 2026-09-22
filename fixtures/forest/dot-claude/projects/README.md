This directory name (`-Users-guydvir-opportunity-radar-kits-six-laws-kit-fixtures-forest-alpha`) is
the forward encoding of the absolute path of `fixtures/forest/alpha` on the machine this fixture was
built on, per `paths.encode_project_dir` (every `/` and `.` replaced by `-`). When a test copies
`fixtures/forest/` into a temporary HOME, `alpha`'s absolute path changes, so this encoded name no
longer matches it. `conftest.py` must re-encode `<temp_home>/forest/alpha` itself (calling the same
forward-encoding logic the installer uses) and rename or look up this directory under the freshly
computed name rather than assuming the name checked into this fixture still applies.
