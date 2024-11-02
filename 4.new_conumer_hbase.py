from kafka import KafkaConsumer
import json
import happybase
import uuid
from datetime import datetime
import time
import socket
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HBaseConnectionError(Exception):
    """Custom exception for HBase connection issues."""
    pass

class DiseasePredictionConsumer:
    def __init__(self, bootstrap_servers=['localhost:29092'], hbase_host='localhost', hbase_port=9090, max_retries=3, retry_delay=5):
        self.bootstrap_servers = bootstrap_servers
        self.hbase_host = hbase_host
        self.hbase_port = hbase_port
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.consumer = None
        self.connection = None

        # Initialize connections
        self._initialize_connections()

    def _initialize_connections(self):
        """Initialize Kafka and HBase connections with retry logic."""
        self._init_kafka_consumer()
        self._init_hbase_connection()

    def _init_kafka_consumer(self):
        """Initialize Kafka consumer with retry logic."""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.consumer = KafkaConsumer(
                    'newst',  # New topic for disease predictions
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    auto_offset_reset='earliest',
                    group_id='disease_prediction_group'
                )
                logger.info("Successfully connected to Kafka")
                break
            except Exception as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    raise Exception(f"Failed to connect to Kafka after {self.max_retries} attempts: {str(e)}")
                logger.warning(f"Kafka connection attempt {retry_count} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

    def _init_hbase_connection(self):
        """Initialize HBase connection with retry logic."""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.connection = happybase.Connection(
                    host=self.hbase_host,
                    port=self.hbase_port,
                    timeout=20000  # Extended timeout
                )
                self.connection.open()  # Explicitly open the connection
                logger.info("Successfully connected to HBase")
                break
            except (socket.error, happybase.hbase.ttypes.IOError) as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    raise HBaseConnectionError(f"Failed to connect to HBase after {self.max_retries} attempts: {str(e)}")
                logger.warning(f"HBase connection attempt {retry_count} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

    def _ensure_table_exists(self, table_name):
        """Ensure HBase table exists for the disease."""
        if table_name.encode() not in self.connection.tables():
            logger.info(f"Table {table_name} does not exist. Creating table...")
            try:
                self.connection.create_table(
                    table_name.encode(),
                    {
                        'info': dict(),      # Column family for disease information
                        'metrics': dict()    # Column family for likelihood and timestamp
                    }
                )
                logger.info(f"Table {table_name} created successfully")
            except Exception as e:
                raise HBaseConnectionError(f"Failed to create HBase table: {str(e)}")
        else:
            logger.info(f"Table {table_name} already exists")

    def _store_in_hbase(self, row_key, data, table_name):
        """Store data in the specified HBase table with retry logic."""
        retry_count = 0
        table = self.connection.table(table_name.encode())
        while retry_count < self.max_retries:
            try:
                table.put(row_key, data)
                return
            except (socket.error, happybase.hbase.ttypes.IOError) as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    raise HBaseConnectionError(f"Failed to store data in HBase after {self.max_retries} attempts: {str(e)}")
                logger.warning(f"HBase storage attempt {retry_count} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
                self._init_hbase_connection()  # Reinitialize HBase connection if storage fails

    def start_consuming(self):
        """Start consuming messages from Kafka and storing them in HBase."""
        logger.info("Starting consumer... Waiting for messages")
        try:
            for message in self.consumer:
                try:
                    data = message.value
                    disease_name = data.get('predicted_class', 'unknown_disease').lower()
                    table_name = f"{disease_name}_pred"  # Table name based on disease name
                    self._ensure_table_exists(table_name)

                    row_key = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}".encode()
                    
                    # Prepare data for HBase insertion
                    disease_data = {
                        b'info:disease_name': disease_name.encode(),
                        b'info:image_path': str(data['image_data']).encode(),
                        b'metrics:likelihood': str(data['likelihood']).encode(),
                        b'metrics:timestamp': str(datetime.now()).encode()
                    }
                    
                    # Store data in the dynamically selected table
                    self._store_in_hbase(row_key, disease_data, table_name)
                    logger.info(f"Stored disease prediction in HBase - Disease: {disease_name}, Key: {row_key.decode()}")
                    
                except HBaseConnectionError as e:
                    logger.error(f"HBase storage error: {str(e)}")
                except KeyError as e:
                    logger.error(f"Invalid message format: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error processing message: {str(e)}")
                    
        except KeyboardInterrupt:
            logger.info("Shutting down consumer...")
        finally:
            self.close()

    def close(self):
        """Close all connections."""
        try:
            if self.consumer:
                self.consumer.close()
            if self.connection:
                self.connection.close()
            logger.info("Connections closed successfully")
        except Exception as e:
            logger.error(f"Error while closing connections: {str(e)}")

if __name__ == "__main__":
    # Configuration
    config = {
        'bootstrap_servers': ['localhost:29092'],
        'hbase_host': 'localhost',
        'hbase_port': 9090,
        'max_retries': 3,
        'retry_delay': 5
    }
    
    try:
        consumer = DiseasePredictionConsumer(**config)
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        exit(1)
