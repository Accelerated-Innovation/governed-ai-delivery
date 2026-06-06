from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def apply_customer_quality(bronze_customers: DataFrame) -> DataFrame:
    return (
        bronze_customers
        .withColumn("email_domain", F.lower(F.substring_index("email", "@", -1)))
        .withColumn("is_valid_email", F.col("email").contains("@"))
    )
