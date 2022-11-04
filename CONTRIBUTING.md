## Coding guidelines

`ldc-bpcsad` follows the official Python guidelines detailed in [PEP8](https://www.python.org/dev/peps/pep-0008) that detail how code should be formatted and indented.

Beyond PEP8, please also:

- Avoid multiple statements on one line.
- Keep lines to 80 fewer or characters whenever possible.
- Use relative imports for references within `ldc-bpcsad`
- Unit tests are an exception to the above rule; always use absolute imports
  within tests.
- **NEVER** use the `import *` pattern.
- Follow the [NumPy docstring standard](https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard). We rely on docstrings meeting this standard to generate the docs with Sphinx.


## Unit testing

### Better local unit tests with `pytest`

Unit testing is done via the excellent `pytest` framework. Install it via
`pip install pytest`.

To run all unit tests:

```bash
pytest ldc-bpcsad/ -v
```

If you want to just run tests that contain a specific substring, you can
use the `-k` flag:

```bash
pytest ldc-bpcsad/ -k hvite -v
```

The above is an example of testing just code calling HVite.


### Local linting

All code should be linted via `pylint` before committing. To insall `pylint`:

```bash
pip install pylint
```

To run on a file:

```bash
pylint some_module.py
```