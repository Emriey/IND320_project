import os

# 1. Set environment variables (safe to include even if already set in Windows)
os.environ["HADOOP_HOME"] = "C:/Hadoop/hadoop-3.3.1" 
os.environ["PYSPARK_HADOOP_VERSION"] = "without"
os.environ["PYSPARK_PYTHON"] = "python"
os.environ["PYSPARK_DRIVER_PYTHON"] = "python"

from pyspark.sql import SparkSession

print("Initializing Spark session...")

# 2. Create Spark Session and pass the Cassandra connector package for Spark 3.5
# Note: The very first time you run this, Spark will take a moment to download the connector jar.
spark = (
    SparkSession.builder.appName("CassandraConnectionTest")
    .config("spark.cassandra.connection.host", "127.0.0.1")
    .config(
        "spark.jars.packages",
        "com.datastax.spark:spark-cassandra-connector_2.12:3.5.1",
    )
    .getOrCreate()
)

print("Spark session created successfully!")

try:
    # 3. Try reading a built-in Cassandra system table to verify the connection
    df = (
        spark.read.format("org.apache.spark.sql.cassandra")
        .options(table="local", keyspace="system")
        .load()
    )

    print(
        "\nSuccess! Connected to Cassandra. Displaying data from system.local:"
    )
    df.select("cluster_name", "release_version", "data_center").show(
        truncate=False
    )

except Exception as e:
    print("\nConnection failed. Error details:")
    print(e)

finally:
    # 4. Clean up
    spark.stop()