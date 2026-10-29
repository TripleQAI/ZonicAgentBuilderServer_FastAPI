#!/usr/bin/env bash
# Deploy the Agent Visual Builder at the lowest standing cost: this API on Lambda
# (arm64 container image, Function URL) and ZonicAgentBuilderUI_NextJS as a static
# export on S3, behind one CloudFront distribution. See cdk/lib/agent-builder-stack.ts.
#
# The public address, https://dev.tripleq.ai/agent-visual-builder-lg/, is served by
# the front door (D:/Zonic/agent-build-run/dev-tripleq-frontdoor), which routes the
# path to this stack's distribution. Run its deploy.sh once after this stack exists.
#
# Idempotent: the first run creates everything; later runs build, push and roll
# forward to the new image and app.
#
# Usage (from this project's root, in Git Bash or Linux, with Docker running):
#   bash deploy/aws-lambda/deploy.sh
#
# Settings: plain values are in cdk/cdk.json ("agentBuilder"). Secret ones are the
# SecureString /zonic-agent-builder-server/secrets (JSON); when it does not exist yet
# it is created from PG_GATEWAY_AUTH_HEADER in .env. Read it with:
#   MSYS_NO_PATHCONV=1 aws ssm get-parameter --name /zonic-agent-builder-server/secrets --with-decryption
#
# Remove everything:
#   aws s3 rm s3://<SiteBucketName> --recursive
#   aws cloudformation delete-stack --stack-name AgentVisualBuilderLgStack
#   aws ecr delete-repository --repository-name zonic-agent-builder-server --force
#
# Overridable environment variables:
#   AWS_PROFILE (default tripleq-development)
#   AWS_REGION  (default us-east-1, the region of the pgfoundation gateway)
#   ECR_REPO    (default zonic-agent-builder-server)
#   IMAGE_TAG   (an image already in ECR_REPO: skips the API build and push)
#   UI_DIR      (default ../ZonicAgentBuilderUI_NextJS)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CDK_DIR="$ROOT/deploy/aws-lambda/cdk"
UI_DIR="${UI_DIR:-$ROOT/../ZonicAgentBuilderUI_NextJS}"
export AWS_PROFILE="${AWS_PROFILE:-tripleq-development}"
REGION="${AWS_REGION:-us-east-1}"
REPO="${ECR_REPO:-zonic-agent-builder-server}"
STACK=AgentVisualBuilderLgStack
ARCH=arm64

log() { printf '\n==> %s\n' "$*"; }

# Windows AWS CLI needs a Windows path for local files.
native_path() { cygpath -w "$1" 2>/dev/null || printf '%s' "$1"; }

aws_() { aws --region "$REGION" "$@"; }
# Git Bash rewrites arguments that start with "/" (parameter names, "/*") into Windows
# paths. Docker needs that rewriting for local paths, so it is off only for these calls.
aws_raw() { MSYS_NO_PATHCONV=1 aws --region "$REGION" "$@"; }

VALUE_FILE="$(mktemp)"
trap 'rm -f "$VALUE_FILE"' EXIT

[ -d "$UI_DIR/src" ] || { echo "No UI project at $UI_DIR (set UI_DIR)." >&2; exit 1; }

ACCOUNT="$(aws_ sts get-caller-identity --query Account --output text)"
REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
TAG="${IMAGE_TAG:-$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo manual)-$(date +%Y%m%d%H%M%S)}"
IMAGE="$REGISTRY/$REPO:$TAG"
log "account $ACCOUNT, region $REGION, profile $AWS_PROFILE"

# --- secrets (SecureString, standard tier: free) -----------------------------
SECRET_PARAMETER="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["context"]["agentBuilder"]["secretParameter"])' \
  "$(native_path "$CDK_DIR/cdk.json")" | tr -d '\r')"
if aws_raw ssm get-parameter --name "$SECRET_PARAMETER" >/dev/null 2>&1; then
  log "secrets: $SECRET_PARAMETER exists"
else
  # The value goes from .env to a temporary file as JSON; it is never printed.
  python - "$(native_path "$ROOT/.env")" "$(native_path "$VALUE_FILE")" <<'EOF'
import json, re, sys
values = {}
for line in open(sys.argv[1], encoding='utf-8-sig'):
    match = re.match(r'\s*(PG_GATEWAY_AUTH_HEADER)\s*=(.*)$', line.rstrip('\r\n'))
    if match and match.group(2).strip():
        values[match.group(1)] = match.group(2).strip().strip('\'"')
if not values:
    sys.exit('No PG_GATEWAY_AUTH_HEADER in .env.')
open(sys.argv[2], 'w', encoding='utf-8').write(json.dumps(values))
EOF
  aws_raw ssm put-parameter --name "$SECRET_PARAMETER" --type SecureString --tier Standard \
    --value "file://$(native_path "$VALUE_FILE")" \
    --description 'Agent Visual Builder API: secret settings (JSON), read by deploy/aws-lambda/start.py' >/dev/null
  log "secrets: created $SECRET_PARAMETER from .env"
fi

# --- API image ---------------------------------------------------------------
log "ECR repository $REPO"
if ! aws_ ecr describe-repositories --repository-names "$REPO" >/dev/null 2>&1; then
  aws_ ecr create-repository --repository-name "$REPO" \
    --image-scanning-configuration scanOnPush=true >/dev/null
fi
# Keep the five newest images so storage stays at cents per month.
aws_ ecr put-lifecycle-policy --repository-name "$REPO" --lifecycle-policy-text \
  '{"rules":[{"rulePriority":1,"description":"keep the 5 newest images","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":5},"action":{"type":"expire"}}]}' \
  >/dev/null

if [ -n "${IMAGE_TAG:-}" ]; then
  log "image $IMAGE (IMAGE_TAG: not rebuilt)"
  aws_ ecr describe-images --repository-name "$REPO" --image-ids imageTag="$TAG" >/dev/null
else
  log "build and push $IMAGE"
  aws_ ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
  # --provenance/--sbom off: Lambda rejects image indexes that carry attestations.
  docker buildx build --platform "linux/$ARCH" --provenance=false --sbom=false \
    -f "$ROOT/deploy/aws-lambda/Dockerfile" -t "$IMAGE" --push "$ROOT"
fi

# --- stack -------------------------------------------------------------------
# CDK writes the template; CloudFormation deploys it. `cdk deploy` would publish the
# template through the bucket `cdk bootstrap` creates, and this account is not
# bootstrapped. The template has no assets and stays under the 51,200 bytes that
# CloudFormation accepts inline.
log "stack $STACK"
TEMPLATE_DIR="$CDK_DIR/cdk.out"
(
  cd "$CDK_DIR"
  [ -d node_modules ] || npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
  CDK_DEFAULT_ACCOUNT="$ACCOUNT" CDK_DEFAULT_REGION="$REGION" npx cdk synth "$STACK" \
    -c backendRepositoryName="$REPO" -c backendImageTag="$TAG" \
    --output "$(native_path "$TEMPLATE_DIR")" --quiet
)
aws_ cloudformation deploy --stack-name "$STACK" \
  --template-file "$(native_path "$TEMPLATE_DIR/$STACK.template.json")" \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset
output() { aws_ cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text | tr -d '\r'; }
APP_URL="$(output AppUrl)"
BASE_PATH="$(output AppBasePath)"   # e.g. /agent-visual-builder-lg
DISTRIBUTION_DOMAIN="$(output DistributionDomainName)"
DISTRIBUTION_ID="$(output DistributionId)"
BUCKET="$(output SiteBucketName)"

# --- app ---------------------------------------------------------------------
# A static export for its path (next.config.ts), stored under it: S3 keys mirror the URLs.
# It is built in a scratch copy of the project: `next build` always rewrites .next/, so building
# in UI_DIR would pull the build out from under a `next start` serving that working copy.
log "build the app for $BASE_PATH and upload it to s3://$BUCKET$BASE_PATH/"
UI_BUILD="$(mktemp -d)"
trap 'rm -f "$VALUE_FILE"; rm -rf "$UI_BUILD"' EXIT
tar -C "$UI_DIR" --exclude=./node_modules --exclude=./.next --exclude=./out -cf - . | tar -C "$UI_BUILD" -xf -
(
  cd "$UI_BUILD"
  npm ci --no-audit --no-fund
  # MSYS_NO_PATHCONV: Git Bash would turn the path into C:/Program Files/Git/...
  MSYS_NO_PATHCONV=1 NEXT_OUTPUT=export NEXT_BASE_PATH="$BASE_PATH" \
    NEXT_PUBLIC_COGNITO_REGION="$(output CognitoRegion)" \
    NEXT_PUBLIC_COGNITO_USER_POOL_ID="$(output CognitoUserPoolId)" \
    NEXT_PUBLIC_COGNITO_CLIENT_ID="$(output CognitoAppClientId)" \
    npx next build
)
# Hashed assets never change; pages must be fetched fresh to pick up a release.
aws_raw s3 sync "$(native_path "$UI_BUILD/out/_next/static")" "s3://$BUCKET$BASE_PATH/_next/static" --delete \
  --cache-control 'public, max-age=31536000, immutable' >/dev/null
aws_raw s3 sync "$(native_path "$UI_BUILD/out")" "s3://$BUCKET$BASE_PATH" --delete --exclude '_next/static/*' \
  --cache-control 'no-cache' >/dev/null
aws_raw cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths '/*' >/dev/null

# --- smoke test --------------------------------------------------------------
# Through this stack's own distribution, which answers before the front door routes to it.
DIRECT="https://$DISTRIBUTION_DOMAIN$BASE_PATH"
log "smoke test $DIRECT"
printf 'health: '
curl -sS --retry 5 --retry-all-errors --retry-delay 3 -m 60 -o /dev/null -w '[HTTP %{http_code}]\n' "$DIRECT/health"
printf 'ready: '
curl -sS -m 60 -o /dev/null -w '[HTTP %{http_code}]\n' "$DIRECT/health/ready"
printf 'agents without a token (expect 401): '
curl -sS -m 60 -o /dev/null -w '[HTTP %{http_code}]\n' "$DIRECT/api/v1/agents"
printf 'app: '
curl -sS -m 60 -o /dev/null -w '[HTTP %{http_code}]\n' "$DIRECT/workflows"

cat <<EOF

App:          $APP_URL  (through the front door)
Distribution: $DISTRIBUTION_DOMAIN
Sign in with the Cognito pool in cdk/cdk.json ("agentBuilder").
EOF
