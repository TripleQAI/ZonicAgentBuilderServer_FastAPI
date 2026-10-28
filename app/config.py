"""Service configuration. Environment-driven, validated at boot.

Note what is absent: there is no DSN, no pool size and no database credential.
Persistence goes through the pgfoundation gateway, so this service holds a URL
and (optionally) one service token (MIGRATION_PLAN.md §7.7).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- data access ------------------------------------------------------
    pg_gateway_base_url: str = "http://localhost:8600"
    pg_gateway_datasource: str = "agentbuilder"
    #: PostgreSQL schema holding the views and procedures. Sent on every
    #: governed call rather than relying on the connection's search_path, which
    #: this service does not control.
    pg_gateway_schema: str = "agent_builder"
    pg_gateway_timeout_ms: int = Field(15_000, gt=0)
    pg_gateway_connect_timeout_ms: int = Field(2_000, gt=0)
    pg_gateway_max_retries: int = Field(2, ge=0, le=5)
    pg_gateway_auth_header: str = ""
    pg_gateway_provider: Literal["http", "fake"] = "http"

    # --- service ----------------------------------------------------------
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    #: Off by default, matching the source: `manage.py seed_node_registry` was
    #: an optional command, and the API serves the JSON registry when the table
    #: is empty. Turn it on only to push the shipped registry into the database
    #: — note that doing so overwrites any row edited there by hand.
    seed_registry_on_startup: bool = False

    # --- sign-in ----------------------------------------------------------
    #: Every /api/v1 route needs a signed-in user. Off only for local tests and
    #: tools that have no user pool.
    auth_required: bool = True
    #: The builder's own Cognito user pool (separate from the Strands builder's)
    #: and its app client. Tokens are ID tokens issued for that client.
    cognito_region: str = "us-east-1"
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""

    # --- embedding --------------------------------------------------------
    embedding_provider: Literal["bedrock", "fake"] = "bedrock"
    aws_default_region: str = "us-east-1"
    aws_bedrock_region: str = ""
    bedrock_embed_model_id: str = "cohere.embed-english-v3"

    @field_validator("pg_gateway_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cognito_issuer(self) -> str:
        return f"https://cognito-idp.{self.cognito_region}.amazonaws.com/{self.cognito_user_pool_id}"

    @property
    def bedrock_region(self) -> str:
        return self.aws_bedrock_region or self.aws_default_region


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
