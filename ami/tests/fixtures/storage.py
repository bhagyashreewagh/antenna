import io
import logging

from django.conf import settings

from ami.main.models import Project, S3StorageSource
from ami.tests.fixtures.images import GeneratedTestFrame, generate_moth_series
from ami.utils import s3

logger = logging.getLogger(__name__)

# PATCHED CONFIG — USE REAL AWS S3 INSTEAD OF MINIO
S3_TEST_CONFIG = s3.S3Config(
    endpoint_url=None,  # let boto3 use the default AWS endpoint
    access_key_id=settings.DJANGO_AWS_ACCESS_KEY_ID,
    secret_access_key=settings.DJANGO_AWS_SECRET_ACCESS_KEY,
    bucket_name=settings.DJANGO_AWS_STORAGE_BUCKET_NAME,
    prefix="demo-data",
    public_base_url=f"https://{settings.DJANGO_AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/demo-data",
)


def create_storage_source(project: Project, name: str, prefix: str = S3_TEST_CONFIG.prefix) -> S3StorageSource:
    # DO NOT TRY TO CREATE A BUCKET (AWS buckets already exist)
    # Just ensure the folder / prefix exists by writing a tiny placeholder file
    placeholder_key = f"{prefix}/.placeholder"

    try:
        s3.write_file(S3_TEST_CONFIG, placeholder_key, b'')
        logger.info(f"Verified S3 prefix: {prefix}")
    except Exception as e:
        logger.error(f"Failed to verify S3 prefix {prefix}: {e}")

    data_source, _created = S3StorageSource.objects.get_or_create(
        project=project,
        name=name,
        defaults=dict(
            bucket=S3_TEST_CONFIG.bucket_name,
            prefix=prefix,
            endpoint_url=S3_TEST_CONFIG.endpoint_url,
            access_key=S3_TEST_CONFIG.access_key_id,
            secret_key=S3_TEST_CONFIG.secret_access_key,
            public_base_url=S3_TEST_CONFIG.public_base_url,
        ),
    )
    return data_source


def populate_bucket(
    config: s3.S3Config,
    subdir: str = "deployment_1",
    num_nights: int = 2,
    images_per_day: int = 3,
    minutes_interval: int = 45,
    minutes_interval_variation: int = 10,
    skip_existing: bool = True,
) -> list[GeneratedTestFrame]:
    created = []

    # Check if subdir already has images
    if skip_existing:
        keys = s3.list_files(config=config, subdir=subdir, limit=10)
        existing_keys = [key.key for key, i in keys if key]
        if existing_keys:
            logger.info(f"Skipping existing images in {subdir}: {existing_keys}")
            return []

    logger.info(f"Generating {num_nights * images_per_day} demo images…")

    for _ in range(num_nights):
        for frame in generate_moth_series(
            num_frames=images_per_day,
            minutes_interval=minutes_interval,
            minutes_interval_variation=minutes_interval_variation,
            save_images=False,
        ):
            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            frame.image.save(img_byte_arr, format="JPEG")
            img_byte_arr = img_byte_arr.getvalue()

            # Construct S3 key
            key = f"{subdir}/{frame.filename}"

            # Upload to REAL S3
            logger.info(f"Uploading {key} → {config.bucket_name}")
            s3.write_file(config, key, img_byte_arr)

            frame.object_store_key = key
            created.append(frame)

    return created
