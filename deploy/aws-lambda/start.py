"""Lambda entry point: secrets from SSM into the environment, then uvicorn.

The app reads its settings from environment variables only (app/config.py). On
Lambda the plain ones are set on the function; the secret ones (the gateway header)
live in the SecureString named by SECRET_PARAMETER, a JSON object of variable names
to values, so they never appear in the function's configuration. Variables already
set win.
"""

from __future__ import annotations

import json
import os

name = os.environ.get("SECRET_PARAMETER")
if name:
    import boto3

    value = boto3.client("ssm").get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
    for key, secret in json.loads(value).items():
        os.environ.setdefault(key, secret)

os.execvp(
    "python",
    ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8080")],
)
