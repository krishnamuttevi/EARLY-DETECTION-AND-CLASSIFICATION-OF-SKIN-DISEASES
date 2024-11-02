from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import os
import base64
from tensorflow.keras.models import load_model
from kafka import KafkaProducer
import json
from kafka.admin import KafkaAdminClient, NewTopic

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

cnn = load_model(r'D:\swastik\docker\dataorch\cleansed_20_epoch.keras')

class_names = ['Basal Cell Carcinoma', 
               'Benign_Keratosis-like_Lesions',
               'Melanocytic_Nevi', 'Melanoma', 
               'Seborrheic_Keratoses_and_other_Benign_Tumors', 
               'Tinea_Ringworm_Candidiasis_and_other_Fungal_Infections'
               ]


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Kafka producer setup
producer = KafkaProducer(
    bootstrap_servers='localhost:29092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def prepare_image(image):
    img = image.convert('RGB')
    img = img.resize((128, 128))
    input_arr = np.array(img)
    input_arr = np.expand_dims(input_arr, axis=0)
    return input_arr

@app.route('/')
def home():
    return '''
        <html>
            <head>
                <title>Skin Disease Prediction API</title>
            </head>
            <body>
                <h1>Skin Disease Prediction</h1>
                <p>Upload an image to get a prediction of possible skin diseases.</p>
            </body>
        </html>
    '''

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if file and allowed_file(file.filename):
        try:
            # Read file content first
            file_content = file.read()  # Store the content of the image
            file.seek(0)  # Reset the file pointer after reading

            # Open the image using PIL for prediction
            img = Image.open(file.stream)
            prepared_image = prepare_image(img)
            predictions = cnn.predict(prepared_image)
            result_index = np.argmax(predictions)
            model_prediction = class_names[result_index]
            likelihood = float(predictions[0][result_index])
            # Send the image and prediction result to Kafka, dynamically creating the topic if needed
            send_image_to_kafka(file_content, model_prediction, likelihood, topic_name='newst')
            return jsonify({
                'predicted_class': model_prediction,
                'likelihood': likelihood
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Unsupported file format. Please upload a PNG, JPG, or JPEG image."}), 400

def send_image_to_kafka(image_content, prediction, likelihood, topic_name='new_topic_name'):
    try:
        # Create the Kafka topic if it doesn't exist
        create_kafka_topic(topic_name)
        
        # Convert image content to base64
        image_bytes = base64.b64encode(image_content).decode('utf-8')

        # Prepare the message
        message = {
            'image_data': image_bytes,
            'predicted_class': prediction,
            'likelihood': likelihood
        }

        # Send to Kafka
        producer.send(topic_name, value=message)
        producer.flush()

        print(f"Image and prediction sent to Kafka topic '{topic_name}'")
    except Exception as e:
        print(f"Error sending image to Kafka: {e}")

        
def create_kafka_topic(topic_name):
    admin_client = KafkaAdminClient(
        bootstrap_servers="localhost:29092",
        client_id='skin_disease_app'
    )

    topic_list = []
    topic_list.append(NewTopic(name=topic_name, num_partitions=1, replication_factor=1))
    try:
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        print(f"Topic '{topic_name}' created successfully.")
    except Exception as e:
        if 'TopicExistsError' in str(e):
            print(f"Topic '{topic_name}' already exists.")
        else:
            print(f"Error creating topic: {e}")
    finally:
        admin_client.close()

if __name__ == '__main__':
    app.run(debug=True)