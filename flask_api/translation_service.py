import pika
import json
import uuid
from config import Config
import logging
import time

class TranslationServiceClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.response = None
        self.corr_id = None

    def connect(self):
        retries = 5
        while retries > 0:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=Config.RABBITMQ_HOST,
                        connection_attempts=5,
                        retry_delay=5
                    )
                )
                self.channel = self.connection.channel()

                result = self.channel.queue_declare(queue='', exclusive=True)
                self.callback_queue = result.method.queue

                self.channel.basic_consume(
                    queue=self.callback_queue,
                    on_message_callback=self.on_response,
                    auto_ack=True
                )
                logging.info("Successfully connected to RabbitMQ")
                return True
            except pika.exceptions.AMQPConnectionError as error:
                logging.warning(f"Failed to connect to RabbitMQ: {error}. Retrying...")
                retries -= 1
                time.sleep(5)
        
        logging.error("Failed to connect to RabbitMQ after multiple attempts")
        return False

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)

    def translate(self, text, target_language):
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                return "Translation service is currently unavailable."

        self.response = None
        self.corr_id = str(uuid.uuid4())

        try:
            self.channel.basic_publish(
                exchange='',
                routing_key='llm_queue',
                properties=pika.BasicProperties(
                    reply_to=self.callback_queue,
                    correlation_id=self.corr_id
                ),
                body=json.dumps({'text': text, 'target_language': target_language})
            )

            while self.response is None:
                self.connection.process_data_events()
            return self.response.get('response', '')
        except pika.exceptions.AMQPConnectionError:
            logging.error("Lost connection to RabbitMQ during translation")
            self.connection = None
            return "Translation service is currently unavailable."