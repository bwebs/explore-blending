import os

import functions_framework
from functions.get_access_grant import get_access_grant
from functions.github_commit_and_deploy import github_commit_and_deploy
from models import AccessGrant, RequestBody
from structlog import get_logger
from werkzeug import Request

PERSONAL_ACCESS_TOKEN = os.environ.get("PERSONAL_ACCESS_TOKEN")

logger = get_logger()

# Shared types between dimensions and measures


@functions_framework.http
def main(request: Request):
    personal_access_token = (
        request.headers.get("X-Personal-Access-Token") or PERSONAL_ACCESS_TOKEN
    )
    if not personal_access_token:
        return "Missing or invalid personal access token", 400

    sdk_client_id = request.headers.get("X-Client-Id")
    sdk_client_secret = request.headers.get("X-Client-Secret")
    sdk_base_url = request.headers.get("X-Base-Url")
    if not sdk_base_url:
        return "Missing or invalid sdk base url", 400
    webhook_secret = request.headers.get("X-Webhook-Secret")

    body = RequestBody.model_validate(request.json)

    access_grant: AccessGrant | None = None
    if sdk_client_id and sdk_client_secret and sdk_base_url:
        ag_response = get_access_grant(
            sdk_client_id=sdk_client_id,
            sdk_client_secret=sdk_client_secret,
            sdk_base_url=sdk_base_url,
            user_attribute=body.user_attribute,
            models=body.models,
            uuid=body.uuid,
        )
        if not ag_response["success"]:
            return dict(success=False, error=ag_response["error"]), 400
        access_grant = ag_response["access_grant"]

    lookml = body.get_lookml(access_grant)

    github_commit_and_deploy(
        lookml=lookml,
        sdk_base_url=sdk_base_url,
        **body.model_dump(),
        personal_access_token=personal_access_token,
        webhook_secret=webhook_secret,
    )
    explore_url = f"/explore/{body.lookml_model}/{body.name}"
    explore_id = f"{body.lookml_model}::{body.name}"

    return dict(
        success=True,
        explore_url=explore_url,
        explore_id=explore_id,
        lookml_model_name=body.lookml_model,
        explore_name=body.name,
    )
