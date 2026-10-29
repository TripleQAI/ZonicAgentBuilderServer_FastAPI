#!/usr/bin/env node
// Run by deploy/aws-lambda/deploy.sh, which pushes the API image first and passes it as
//   -c backendRepositoryName=<repo> -c backendImageTag=<tag>

import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AgentBuilderStack } from '../lib/agent-builder-stack';

const app = new cdk.App();

const backendRepositoryName = app.node.tryGetContext('backendRepositoryName');
const backendImageTag = app.node.tryGetContext('backendImageTag');
if (!backendRepositoryName || !backendImageTag) {
  throw new Error('Pass -c backendRepositoryName=<repo> -c backendImageTag=<tag> (deploy/aws-lambda/deploy.sh does)');
}

new AgentBuilderStack(app, 'AgentVisualBuilderLgStack', {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },
  backendRepositoryName,
  backendImageTag,
  // No bootstrap version rule and no assets (the deploy script pushes the image), so
  // deploy.sh hands the template straight to CloudFormation: no `cdk bootstrap`.
  synthesizer: new cdk.CliCredentialsStackSynthesizer(),
});
