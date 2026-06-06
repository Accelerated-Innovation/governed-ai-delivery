# Databricks notebook source

# COMMAND ----------

from src.silver.customer_quality import apply_customer_quality


def main():
    bronze = spark.table("dev_catalog.customer_analytics_dev.bronze_customers")
    silver = apply_customer_quality(bronze)
    silver.write.mode("overwrite").saveAsTable("dev_catalog.customer_analytics_dev.silver_customers")


main()
