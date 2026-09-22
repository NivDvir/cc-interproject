# ML Lab

Scratch space for training experiments. Nothing here is production code.

Every experiment lives in `experiments/<date>-<slug>/` with its own config file and a
`README.md` recording what question it was meant to answer.

Checkpoints are large and are not committed. They go to the object store bucket named
in `config/storage.yaml`, under the experiment's own prefix.

The notebooks are exploratory. If a result matters, it gets rewritten as a script
before it is quoted anywhere.
