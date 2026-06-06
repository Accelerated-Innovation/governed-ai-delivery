from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def build_customer_dimension(silver_customers: DataFrame) -> DataFrame:
    return (
        silver_customers
        .where(F.col("is_valid_email"))
        .select("customer_id", "email_domain", "created_at")
    )
