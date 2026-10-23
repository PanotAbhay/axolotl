# runner

Sandbox image for executing fixture code. Owner: **Dev 4**.

```bash
docker build -t axolotl-runner:latest runner/
```

The image contains Python 3.12 and pytest and nothing else — no project code, no cases,
no credentials. Everything is bind-mounted read-only at run time.

See [policy.md](policy.md) for the exact `docker run` profile, the three gate commands,
and an honest statement of what the sandbox does and does not protect against.

`harness/run_cases.py` is standard-library only and must never import from the backend.
