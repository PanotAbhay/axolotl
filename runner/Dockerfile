# Axolotl sandbox runner - owner: Dev 4.
#
# Build from the repo root:
#     docker build -t axolotl-runner:latest runner/
#
# This image never contains project code, cases or credentials. The candidate
# tree, the harness and the cases file are all bind-mounted read-only at run
# time, and no environment variables are passed in. See runner/policy.md.

FROM python:3.12-slim

# /code is read-only at run time, so bytecode cannot be written next to sources.
# PYTHONDONTWRITEBYTECODE is not enough: `compileall` writes bytecode by design and
# ignores it, so PYTHONPYCACHEPREFIX redirects every .pyc into the tmpfs instead.
# uid 65534 (nobody) has no home either, so HOME and TMPDIR point at the tmpfs too.
#
# PYTHONPATH=/code puts the candidate tree's top-level modules on the path. pytest's
# prepend import mode would otherwise insert only /code/tests (tests/ has no
# __init__.py), and `import pricing` from a test would fail.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PYTHONPYCACHEPREFIX=/tmp/pycache \
    PYTHONPATH=/code \
    HOME=/tmp \
    TMPDIR=/tmp \
    PYTEST_ADDOPTS="-p no:cacheprovider"

# pytest is preinstalled so no gate ever needs network access at run time
# (the container runs with --network none).
RUN pip install --no-cache-dir "pytest==8.3.3" \
    && python -m compileall -q /usr/local/lib/python3.12 >/dev/null 2>&1 || true

WORKDIR /

# No ENTRYPOINT: the backend supplies the exact command per gate
#   differential   python /harness/run_cases.py --code /code --cases /cases.json
#   compile        python -m compileall -q /code
#   existing_tests pytest -q -p no:cacheprovider /code/tests
CMD ["python", "-c", "import sys, pytest; print('axolotl-runner', sys.version)"]
