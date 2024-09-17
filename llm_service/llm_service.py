import pika
import json
import os
from ollama import Client

# RabbitMQ connection parameters
rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')

connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
channel = connection.channel()
channel.queue_declare(queue='llm_queue')

def on_request(ch, method, props, body):
    message = json.loads(body.decode())
    input_text = message.get('text', '')
    target_language = message.get('target_language', 'en')

    # Process input with Llama3 using Ollama Client
    client = Client(host='http://localhost:11434')
    response = client.chat(model='dolphin-llama3', messages=[
        {
            'role': 'user',
            'content': 'translate this to ' + 'Mexican Spanish' + ': ' + input_text,
        },
    ])

    # Extract the response content
    response_content = response['choices'][0]['message']['content']

    # Send response back
    ch.basic_publish(
        exchange='',
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=json.dumps({'response': response_content})
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='llm_queue', on_message_callback=on_request)

print(" [x] Awaiting RPC requests")
channel.start_consuming()