-- 002_schema.sql — tables.
--
-- Translated from the Django models in ZonicAgentBuilderPortal_DjangoApp
-- (agentBuilder/models.py) per MIGRATION_PLAN.md §8.5. Django's "blank=True"
-- convention becomes NOT NULL DEFAULT '' rather than a nullable column, so the
-- application never has to distinguish NULL from empty.
--
-- Idempotent: safe to re-run.

-- --------------------------------------------------------------------------
-- schema_migrations — what is deployed here. Stamped by every file.
-- The application reads it and warns; it never writes DDL.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     varchar(64)  PRIMARY KEY,
    applied_at  timestamptz  NOT NULL DEFAULT now(),
    checksum    varchar(64)  NOT NULL DEFAULT ''
);

-- --------------------------------------------------------------------------
-- agent_workflow — the aggregate root.
--
-- nodes/edges/variables/interface/skills/publish_channels/security are
-- first-class columns AND are mirrored inside raw_json, which preserves the
-- complete original payload so unknown keys survive a round trip. The overlay
-- rule lives in v_agent_export (009) and sp_agent_workflow_save (010).
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_workflow (
    id                          uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    agentic_workflow_id         uuid          NOT NULL UNIQUE,

    bpc                         varchar(100)  NOT NULL DEFAULT '',
    name                        varchar(255)  NOT NULL,
    display_name                varchar(255)  NOT NULL DEFAULT '',
    description                 text          NOT NULL DEFAULT '',
    edit_as                     varchar(100)  NOT NULL DEFAULT '',
    invocation_type             varchar(100)  NOT NULL DEFAULT '',

    is_disabled                 boolean       NOT NULL DEFAULT false,
    is_available_for_migration  boolean       NOT NULL DEFAULT false,
    enable_for_auto_invoke      boolean       NOT NULL DEFAULT false,
    include_thoughts            boolean       NOT NULL DEFAULT false,

    app_id                      varchar(255)  NOT NULL DEFAULT '',
    module_id                   varchar(255)  NOT NULL DEFAULT '',
    environment                 varchar(100)  NOT NULL DEFAULT '',
    version_label               varchar(100)  NOT NULL DEFAULT '',

    is_root                     boolean       NOT NULL DEFAULT false,
    parent_package_id           uuid,

    nodes                       jsonb         NOT NULL DEFAULT '[]'::jsonb,
    edges                       jsonb         NOT NULL DEFAULT '[]'::jsonb,
    variables                   jsonb         NOT NULL DEFAULT '{}'::jsonb,
    interface                   jsonb         NOT NULL DEFAULT '{}'::jsonb,
    skills                      jsonb         NOT NULL DEFAULT '[]'::jsonb,
    publish_channels            jsonb         NOT NULL DEFAULT '[]'::jsonb,
    security                    jsonb         NOT NULL DEFAULT '{}'::jsonb,
    raw_json                    jsonb         NOT NULL DEFAULT '{}'::jsonb,

    semantic_search_enabled     boolean       NOT NULL DEFAULT false,
    semantic_domain             varchar(100)  NOT NULL DEFAULT '',
    semantic_keywords           text          NOT NULL DEFAULT '',
    semantic_use_cases          text          NOT NULL DEFAULT '',

    embedding_vector            jsonb,
    embedding_text              text          NOT NULL DEFAULT '',
    embedding_updated_at        timestamptz,

    created_at                  timestamptz   NOT NULL DEFAULT now(),
    updated_at                  timestamptz   NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------------
-- agent_relationship — parent -> child edges derived from the canvas.
-- Rebuilt from scratch on every save; derivation happens in Python (plan §8.4).
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_relationship (
    id                          uuid          PRIMARY KEY DEFAULT gen_random_uuid(),

    parent_agent_id             uuid          NOT NULL
                                  REFERENCES agent_workflow(id) ON DELETE CASCADE,
    child_agent_id              uuid
                                  REFERENCES agent_workflow(id) ON DELETE SET NULL,

    parent_agentic_workflow_id  uuid          NOT NULL,
    child_agentic_workflow_id   uuid          NOT NULL,

    source_node_id              varchar(255)  NOT NULL DEFAULT '',
    source_node_name            varchar(255)  NOT NULL DEFAULT '',
    source_node_type            varchar(100)  NOT NULL DEFAULT 'workflow',
    relationship_type           varchar(100)  NOT NULL DEFAULT 'sub_flow',

    config_inputs               jsonb         NOT NULL DEFAULT '{}'::jsonb,
    agent_info                  jsonb         NOT NULL DEFAULT '{}'::jsonb,
    app_info                    jsonb         NOT NULL DEFAULT '{}'::jsonb,
    module_info                 jsonb         NOT NULL DEFAULT '{}'::jsonb,

    is_resolved                 boolean       NOT NULL DEFAULT false,
    validation_message          text          NOT NULL DEFAULT '',

    created_at                  timestamptz   NOT NULL DEFAULT now(),
    updated_at                  timestamptz   NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------------
-- agent_workflow_chip — denormalised label row, written with the agent.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_workflow_chip (
    id                    uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    agentic_workflow_id   uuid          NOT NULL UNIQUE,
    bpc                   varchar(100)  NOT NULL DEFAULT '',
    name                  varchar(255)  NOT NULL,
    display_name          varchar(255)  NOT NULL DEFAULT '',
    description           text          NOT NULL DEFAULT '',
    is_disabled           boolean       NOT NULL DEFAULT false
);

-- --------------------------------------------------------------------------
-- workflow_snapshot — point-in-time copies.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflow_snapshot (
    id                 uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_workflow_id  uuid         NOT NULL
                         REFERENCES agent_workflow(id) ON DELETE CASCADE,
    snapshot_json      jsonb        NOT NULL,
    comment            text         NOT NULL DEFAULT '',
    created_at         timestamptz  NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------------------
-- node_type_definition — DB mirror of the JSON node registry.
-- The API prefers this table and falls back to the JSON resources when empty,
-- exactly as the Django app did.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS node_type_definition (
    id                   uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    type                 varchar(100)  NOT NULL UNIQUE,
    label                varchar(255)  NOT NULL,
    icon                 varchar(100)  NOT NULL DEFAULT '',
    color                varchar(50)   NOT NULL DEFAULT '',
    description          text          NOT NULL DEFAULT '',
    default_name_prefix  varchar(100)  NOT NULL DEFAULT '',
    default_config       jsonb         NOT NULL DEFAULT '{}'::jsonb,
    handles              jsonb         NOT NULL DEFAULT '{}'::jsonb,
    form_schema          jsonb         NOT NULL DEFAULT '{}'::jsonb,
    output_schema        jsonb         NOT NULL DEFAULT '{}'::jsonb,
    validation_schema    jsonb         NOT NULL DEFAULT '{}'::jsonb,
    sort_order           integer       NOT NULL DEFAULT 0,
    is_active            boolean       NOT NULL DEFAULT true
);

-- --------------------------------------------------------------------------
-- tool_definition — tool catalogue for the picker.
-- Django's choices become a real CHECK constraint.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tool_definition (
    id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    name            varchar(255)  NOT NULL,
    title           varchar(255)  NOT NULL DEFAULT '',
    description     text          NOT NULL DEFAULT '',
    tool_type       varchar(50)   NOT NULL DEFAULT 'function'
                      CHECK (tool_type IN ('function', 'handoff', 'ui_view', 'mcp')),
    schema          jsonb         NOT NULL DEFAULT '{}'::jsonb,
    default_config  jsonb         NOT NULL DEFAULT '{}'::jsonb,
    is_active       boolean       NOT NULL DEFAULT true,
    created_at      timestamptz   NOT NULL DEFAULT now(),
    updated_at      timestamptz   NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tool_definition_name ON tool_definition (name);

INSERT INTO schema_migrations (version) VALUES ('002_schema')
    ON CONFLICT (version) DO NOTHING;
