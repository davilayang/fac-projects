import logging

from boto3 import client
from botocore.client import Config

from arxiv_rag.config import get_settings

settings = get_settings()

s3 = client(
    "s3",
    region_name="hel1",
    endpoint_url="https://hel1.your-objectstorage.com",
    aws_access_key_id=settings.s3_access_key.get_secret_value(),
    aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
    config=Config(
        signature_version="s3v4",
        s3={
            "payload_signing_enabled": False,
            "addressing_style": "virtual",
        },
    ),
)

BUCKET = settings.s3_bucket_name
PREFIX = "arxiv_rag/"
EXTRACTED_PREFIX = f"{PREFIX}extracted/"


def create_bucket(bucket: str) -> None:
    s3.create_bucket(Bucket=bucket)
    logging.info(f"Created bucket: {bucket}")


def put_object(key: str, body: str) -> None:
    s3.put_object(Bucket=BUCKET, Key=f"{PREFIX}{key}", Body=body)
    logging.info(f"Uploaded: {PREFIX}{key}")


def get_object(key: str) -> str:
    response = s3.get_object(Bucket=BUCKET, Key=f"{PREFIX}{key}")
    return response["Body"].read().decode("utf-8")


def list_objects(prefix: str = PREFIX, suffix: str = ".md") -> list[str]:
    """Return keys (without prefix) matching the given suffix."""
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"][len(prefix) :]
            if key.endswith(suffix):
                keys.append(key)
    return keys


def list_extracted() -> list[str]:
    """Return filenames (e.g. '2301.12345.md') from the extracted/ prefix."""
    return list_objects(prefix=EXTRACTED_PREFIX)


def get_extracted(filename: str) -> str:
    """Read a file from the extracted/ prefix by filename."""
    response = s3.get_object(Bucket=BUCKET, Key=f"{EXTRACTED_PREFIX}{filename}")
    return response["Body"].read().decode("utf-8")
