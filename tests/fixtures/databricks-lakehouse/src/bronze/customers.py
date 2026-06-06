from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def normalize_raw_customers(raw: DataFrame) -> DataFrame:
    return (
        raw.select(
            F.col("customer_id").cast("string").alias("customer_id"),
            F.col("email").cast("string").alias("email"),
            F.col("created_at").cast("timestamp").alias("created_at"),
        )
        .where(F.col("customer_id").isNotNull())
    )
