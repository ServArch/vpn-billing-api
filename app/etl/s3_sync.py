import asyncio
import gzip
import json
import logging
import random
from datetime import datetime, timezone
from io import BytesIO
import aioboto3
from botocore.exceptions import ClientError, EndpointConnectionError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import async_session_maker
from app.models.core import Transaction, User

logger = logging.getLogger("etl.s3_sync")


class BillingDataExporter:
    def __init__(self, chunk_size: int = 500, max_retries: int = 4, base_delay: float = 1.0):
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.session = aioboto3.Session()

    async def extract_billing_records(self, db: AsyncSession) -> dict:
        records: list[dict] = []
        offset = 0

        while True:
            stmt = (
                select(Transaction)
                .order_by(Transaction.id)
                .offset(offset)
                .limit(self.chunk_size)
            )
            result = await db.execute(stmt)
            batch = result.scalars().all()
            if not batch:
                break

            for tx in batch:
                records.append({
                    "id": tx.id,
                    "user_id": tx.user_id,
                    "external_payment_id": tx.external_payment_id,
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "status": tx.status.value if hasattr(tx.status, "value") else str(tx.status),
                    "created_at": tx.created_at.isoformat() if tx.created_at else None,
                })
            offset += len(batch)

        users_count_stmt = select(User.id)
        users_res = await db.execute(users_count_stmt)
        total_users = len(users_res.scalars().all())

        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_transactions": len(records),
            "total_users": total_users,
            "transactions": records,
        }

    async def upload_backup_to_s3(self, data: dict) -> str:
        raw_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        compressed_buf = BytesIO()
        with gzip.GzipFile(fileobj=compressed_buf, mode="wb") as gz:
            gz.write(raw_bytes)
        compressed_payload = compressed_buf.getvalue()

        now = datetime.now(timezone.utc)
        date_folder = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%H%M%S")
        key = f"backups/{date_folder}/billing_dump_{timestamp}.json.gz"

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self.session.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                    region_name=settings.S3_REGION,
                ) as s3_client:
                    try:
                        await s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
                    except ClientError as exc:
                        code = exc.response.get("Error", {}).get("Code")
                        if code in ("404", "NoSuchBucket"):
                            await s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                        else:
                            raise

                    await s3_client.put_object(
                        Bucket=settings.S3_BUCKET_NAME,
                        Key=key,
                        Body=compressed_payload,
                        ContentType="application/gzip",
                    )
                return key
            except (EndpointConnectionError, ClientError, TimeoutError, OSError) as exc:
                last_error = exc
                # Exponential backoff with jitter on transient network/proxy errors
                sleep_time = (self.base_delay * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
                if attempt == self.max_retries:
                    break
                await asyncio.sleep(sleep_time)

        raise RuntimeError(f"Failed to upload backup to S3 after {self.max_retries} attempts: {last_error}")


async def run_sync_job() -> str:
    exporter = BillingDataExporter()
    async with async_session_maker() as session:
        data = await exporter.extract_billing_records(session)
    return await exporter.upload_backup_to_s3(data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dest_key = asyncio.run(run_sync_job())
    print(f"Export completed: {dest_key}")
