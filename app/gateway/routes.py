"""The gateway URL templates. The only place these paths are written."""

from __future__ import annotations

VIEW = "/v1/datasources/{datasource}/view"
PROCEDURE = "/v1/datasources/{datasource}/procedure"
FUNCTION = "/v1/datasources/{datasource}/function"
BATCH = "/v1/batch"
READY = "/ready"
