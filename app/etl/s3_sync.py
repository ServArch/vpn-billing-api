import gzip
import json
from datetime import datetime, timezone
from io import BytesIO
import aioboto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.core import Transaction, Subscription, User


class BillingDataExporter:
    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size
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

        async with self.session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        ) as s3_client:
            # create bucket if not existing
            try:
                await s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
            except Exception:
                await s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)

            await s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=key,
                Body=compressed_payload,
                ContentType="application/gzip",
            )

        return key
