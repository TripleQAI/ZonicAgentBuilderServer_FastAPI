// The Agent Visual Builder on AWS at the lowest standing cost: this API and the
// static export of ZonicAgentBuilderUI_NextJS, under one path.
//
//   CloudFront ─┬─ default ──────────────────────── S3 bucket, keys under <basePath>/
//               │                                    (the exported Next.js app)
//               └─ <basePath>/api/*, /health ... ─── Lambda Function URL (the API image,
//                                                    unchanged, through the Lambda Web
//                                                    Adapter; the prefix is stripped)
//
// No VPC, load balancer or always-on compute: at dev traffic the cost is Lambda and
// CloudFront usage inside their free tiers plus cents of S3 and ECR storage. The
// public host (dev.tripleq.ai) is not here: the front door in
// dev-tripleq-frontdoor/ routes <basePath>/* to this distribution, so this app
// deploys and changes on its own.

import * as cdk from 'aws-cdk-lib';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

/** The API's routes; everything else under basePath is the exported app. */
const API_PATHS = ['/api/*', '/health', '/health/*'];

/** cdk.json "agentBuilder". */
interface AgentBuilderContext {
  /** The address people open, e.g. https://dev.tripleq.ai/agent-visual-builder-lg/ */
  publicUrl: string;
  /** The path the app and API are served under (no trailing slash). */
  basePath: string;
  cognitoRegion: string;
  cognitoUserPoolId: string;
  cognitoAppClientId: string;
  pgGatewayBaseUrl: string;
  pgGatewayDatasource: string;
  pgGatewaySchema: string;
  embeddingProvider: string;
  bedrockEmbedModelId: string;
  /** SecureString with the secret settings as JSON (deploy.sh writes it). */
  secretParameter: string;
}

export interface AgentBuilderStackProps extends cdk.StackProps {
  backendRepositoryName: string;
  backendImageTag: string;
}

export class AgentBuilderStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: AgentBuilderStackProps) {
    super(scope, id, props);

    const settings: AgentBuilderContext = this.node.tryGetContext('agentBuilder') ?? {};
    const required = ['publicUrl', 'basePath', 'cognitoUserPoolId', 'cognitoAppClientId', 'pgGatewayBaseUrl',
      'pgGatewayDatasource', 'pgGatewaySchema', 'secretParameter'] as const;
    const missing = required.filter((key) => !settings[key]);
    if (missing.length) throw new Error(`cdk.json context "agentBuilder" needs ${missing.join(', ')}`);
    const { basePath } = settings;
    if (!/^(\/[a-z0-9-]+)+$/.test(basePath)) throw new Error('agentBuilder.basePath must look like /agent-visual-builder-lg');

    // --- API ----------------------------------------------------------------------
    const logGroup = new logs.LogGroup(this, 'ApiLogs', {
      logGroupName: '/aws/lambda/zonic-agent-builder-server',
      retention: logs.RetentionDays.TWO_WEEKS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const api = new lambda.DockerImageFunction(this, 'Api', {
      functionName: 'zonic-agent-builder-server',
      description: 'Agent Visual Builder API (FastAPI through the Lambda Web Adapter)',
      code: lambda.DockerImageCode.fromEcr(
        ecr.Repository.fromRepositoryName(this, 'ApiRepository', props.backendRepositoryName),
        { tagOrDigest: props.backendImageTag },
      ),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 1024,
      timeout: cdk.Duration.seconds(120),
      logGroup,
      environment: {
        SECRET_PARAMETER: settings.secretParameter,
        PG_GATEWAY_PROVIDER: 'http',
        PG_GATEWAY_BASE_URL: settings.pgGatewayBaseUrl,
        PG_GATEWAY_DATASOURCE: settings.pgGatewayDatasource,
        PG_GATEWAY_SCHEMA: settings.pgGatewaySchema,
        CORS_ORIGINS: new URL(settings.publicUrl).origin,
        AUTH_REQUIRED: 'true',
        COGNITO_REGION: settings.cognitoRegion,
        COGNITO_USER_POOL_ID: settings.cognitoUserPoolId,
        COGNITO_APP_CLIENT_ID: settings.cognitoAppClientId,
        EMBEDDING_PROVIDER: settings.embeddingProvider,
        AWS_BEDROCK_REGION: this.region,
        BEDROCK_EMBED_MODEL_ID: settings.bedrockEmbedModelId,
        SEED_REGISTRY_ON_STARTUP: 'false',
        LOG_LEVEL: 'INFO',
      },
    });

    api.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ssm:GetParameter'],
      resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter${settings.secretParameter}`],
    }));
    if (settings.embeddingProvider === 'bedrock') {
      api.addToRolePolicy(new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel'],
        resources: [`arn:aws:bedrock:${this.region}::foundation-model/${settings.bedrockEmbedModelId}`],
      }));
    }

    // Public at the URL layer: every /api/v1 route checks the Cognito token itself.
    const apiUrl = api.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      invokeMode: lambda.InvokeMode.RESPONSE_STREAM,
    });
    // Since October 2025 a public Function URL also needs lambda:InvokeFunction
    // granted through the URL; addFunctionUrl adds only lambda:InvokeFunctionUrl.
    new lambda.CfnPermission(this, 'ApiUrlInvokeFunction', {
      functionName: api.functionName,
      action: 'lambda:InvokeFunction',
      principal: '*',
      invokedViaFunctionUrl: true,
    });

    // --- app ----------------------------------------------------------------------
    const siteBucket = new s3.Bucket(this, 'Site', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      // Empty it first (deploy.sh prints how); no custom resource does it for you.
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // The export writes /workflows as workflows.html; the bare path redirects to the app.
    const siteRouter = new cloudfront.Function(this, 'SiteRouter', {
      comment: 'Redirect to the app; map its pages to the exported .html files',
      runtime: cloudfront.FunctionRuntime.JS_2_0,
      code: cloudfront.FunctionCode.fromInline(`function handler(event) {
  var request = event.request;
  var base = '${basePath}';
  if (request.uri === '/' || request.uri === base) {
    return { statusCode: 302, statusDescription: 'Found', headers: { location: { value: base + '/' } } };
  }
  if (request.uri.slice(-1) === '/') {
    request.uri += 'index.html';
  } else if (request.uri.split('/').pop().indexOf('.') === -1) {
    request.uri += '.html';
  }
  return request;
}`),
    });
    // The API serves its routes at the root; the app calls them under basePath.
    const stripBasePath = new cloudfront.Function(this, 'StripBasePath', {
      comment: 'Remove the app path before the API',
      runtime: cloudfront.FunctionRuntime.JS_2_0,
      code: cloudfront.FunctionCode.fromInline(`function handler(event) {
  var request = event.request;
  request.uri = request.uri.substring(${basePath.length}) || '/';
  return request;
}`),
    });

    const apiBehavior: cloudfront.BehaviorOptions = {
      origin: new origins.FunctionUrlOrigin(apiUrl, {
        readTimeout: cdk.Duration.seconds(60),
        keepaliveTimeout: cdk.Duration.seconds(60),
      }),
      viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
      cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
      // A Function URL answers only to its own Host.
      originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
      functionAssociations: [{ function: stripBasePath, eventType: cloudfront.FunctionEventType.VIEWER_REQUEST }],
    };

    const distribution = new cloudfront.Distribution(this, 'Distribution', {
      comment: 'Agent Visual Builder (LangGraph) - reached through dev.tripleq.ai',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(siteBucket),
        functionAssociations: [{ function: siteRouter, eventType: cloudfront.FunctionEventType.VIEWER_REQUEST }],
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      additionalBehaviors: Object.fromEntries(API_PATHS.map((path) => [`${basePath}${path}`, apiBehavior])),
    });

    new cdk.CfnOutput(this, 'AppUrl', { value: settings.publicUrl });
    new cdk.CfnOutput(this, 'AppBasePath', { value: basePath });
    new cdk.CfnOutput(this, 'DistributionDomainName', { value: distribution.distributionDomainName });
    new cdk.CfnOutput(this, 'DistributionId', { value: distribution.distributionId });
    new cdk.CfnOutput(this, 'SiteBucketName', { value: siteBucket.bucketName });
    new cdk.CfnOutput(this, 'ApiFunctionUrl', { value: apiUrl.url });
    new cdk.CfnOutput(this, 'CognitoRegion', { value: settings.cognitoRegion });
    new cdk.CfnOutput(this, 'CognitoUserPoolId', { value: settings.cognitoUserPoolId });
    new cdk.CfnOutput(this, 'CognitoAppClientId', { value: settings.cognitoAppClientId });
  }
}
