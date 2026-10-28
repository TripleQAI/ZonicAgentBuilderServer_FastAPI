#!/usr/bin/env bash
# Creates the Agent Workflow Builder's own Cognito user pool and app client, separate
# from the Strands Visual Builder's pool, and writes their IDs into this service's .env
# and the UI's .env.local. Run again at any time: an existing pool and client of the
# same names are reused. Optionally creates a first user (password typed, never echoed).
#
#   AWS_PROFILE=tripleq-development bash scripts/create-user-pool.sh [user-email]
#
# Needs: an AWS CLI session (aws sso login --profile tripleq-development) and node.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${COGNITO_REGION:-us-east-1}"
POOL_NAME="${POOL_NAME:-zonic-agent-builder-users}"
CLIENT_NAME="${CLIENT_NAME:-zonic-agent-builder-ui}"
UI_DIR="${UI_DIR:-../ZonicAgentBuilderUI_NextJS}"
USER_EMAIL="${1:-}"
aws_() { aws --region "$REGION" "$@"; }

POOL_ID="$(aws_ cognito-idp list-user-pools --max-results 60 \
  --query "UserPools[?Name=='$POOL_NAME'].Id | [0]" --output text)"
if [ "$POOL_ID" = "None" ] || [ -z "$POOL_ID" ]; then
  POOL_ID="$(aws_ cognito-idp create-user-pool --pool-name "$POOL_NAME" \
    --username-attributes email --auto-verified-attributes email \
    --admin-create-user-config AllowAdminCreateUserOnly=true \
    --policies 'PasswordPolicy={MinimumLength=12,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false}' \
    --account-recovery-setting 'RecoveryMechanisms=[{Priority=1,Name=verified_email}]' \
    --query UserPool.Id --output text)"
  echo "created user pool $POOL_NAME: $POOL_ID"
else
  echo "using existing user pool $POOL_NAME: $POOL_ID"
fi

CLIENT_ID="$(aws_ cognito-idp list-user-pool-clients --user-pool-id "$POOL_ID" --max-results 60 \
  --query "UserPoolClients[?ClientName=='$CLIENT_NAME'].ClientId | [0]" --output text)"
if [ "$CLIENT_ID" = "None" ] || [ -z "$CLIENT_ID" ]; then
  # A public client (no secret): the browser signs in with SRP, so no password leaves it.
  CLIENT_ID="$(aws_ cognito-idp create-user-pool-client --user-pool-id "$POOL_ID" \
    --client-name "$CLIENT_NAME" --no-generate-secret \
    --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --prevent-user-existence-errors ENABLED \
    --id-token-validity 60 --access-token-validity 60 --refresh-token-validity 30 \
    --token-validity-units 'IdToken=minutes,AccessToken=minutes,RefreshToken=days' \
    --query UserPoolClient.ClientId --output text)"
  echo "created app client $CLIENT_NAME: $CLIENT_ID"
else
  echo "using existing app client $CLIENT_NAME: $CLIENT_ID"
fi

# Writes KEY=value into an env file: replaces the line, or appends it.
set_env() {
  local file="$1" key="$2" value="$3"
  touch "$file"
  if grep -q "^$key=" "$file"; then
    node -e 'const fs=require("fs");const [f,k,v]=process.argv.slice(1);fs.writeFileSync(f,fs.readFileSync(f,"utf8").replace(new RegExp("^"+k+"=.*$","m"),k+"="+v));' "$file" "$key" "$value"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}
set_env .env AUTH_REQUIRED true
set_env .env COGNITO_REGION "$REGION"
set_env .env COGNITO_USER_POOL_ID "$POOL_ID"
set_env .env COGNITO_APP_CLIENT_ID "$CLIENT_ID"
echo "wrote COGNITO_* to $(pwd)/.env"
if [ -d "$UI_DIR" ]; then
  set_env "$UI_DIR/.env.local" NEXT_PUBLIC_COGNITO_REGION "$REGION"
  set_env "$UI_DIR/.env.local" NEXT_PUBLIC_COGNITO_USER_POOL_ID "$POOL_ID"
  set_env "$UI_DIR/.env.local" NEXT_PUBLIC_COGNITO_CLIENT_ID "$CLIENT_ID"
  echo "wrote NEXT_PUBLIC_COGNITO_* to $UI_DIR/.env.local (rebuild the UI to use them)"
fi

if [ -n "$USER_EMAIL" ]; then
  if ! aws_ cognito-idp admin-get-user --user-pool-id "$POOL_ID" --username "$USER_EMAIL" >/dev/null 2>&1; then
    aws_ cognito-idp admin-create-user --user-pool-id "$POOL_ID" --username "$USER_EMAIL" \
      --user-attributes Name=email,Value="$USER_EMAIL" Name=email_verified,Value=true \
      --message-action SUPPRESS >/dev/null
    echo "created user $USER_EMAIL"
  fi
  read -r -s -p "Password for $USER_EMAIL (12+ characters, upper and lower case, a number): " PASSWORD
  echo
  aws_ cognito-idp admin-set-user-password --user-pool-id "$POOL_ID" --username "$USER_EMAIL" \
    --password "$PASSWORD" --permanent
  unset PASSWORD
  echo "password set for $USER_EMAIL"
fi
