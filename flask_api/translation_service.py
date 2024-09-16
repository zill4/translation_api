import pika
import json
import uuid
from config import Config

class TranslationServiceClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=Config.RABBITMQ_HOST))
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.response = None
        self.corr_id = None

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)

    def translate(self, text, target_language):
        self.response = None
        self.corr_id = str(uuid.uuid4())

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