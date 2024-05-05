import azure.functions as func
import logging
import os
import uuid
import requests
from bs4 import BeautifulSoup
from azure.ai.textanalytics import TextAnalyticsClient, ExtractiveSummaryAction
from azure.core.credentials import AzureKeyCredential

# Initialize Azure Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="AzLINETextSummarization", methods=['POST'])
def az_ai_text_summarize(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function to summarize and translate text from a URL, and send it via LINE Messaging API."""
    logging.info('Processing the HTTP request in Python Azure Function.')

    try:
        # Extract the JSON data from the incoming request
        data = req.get_json()
        url_to_summarize = data.get('url')
        
        # Validate that the URL is provided
        if not url_to_summarize:
            return func.HttpResponse("Please provide a URL in the request body.", status_code=400)
        
        # Extract the text from the specified URL
        extracted_text = extract_text_from_url(url_to_summarize)
        if not extracted_text:
            return func.HttpResponse("Failed to extract text from the provided URL.", status_code=500)

        # Initialize Azure clients for Text Analytics and OpenAI
        text_analytics_client = get_text_analytics_client()

        # Summarize and translate the text
        translated_summary = summarize_and_translate(text_analytics_client, extracted_text)
        if not translated_summary:
            return func.HttpResponse("Failed to generate a translated summary.", status_code=500)

        # Send the translated summary via LINE Messaging API
        line_channel_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        result = send_line_message(line_channel_token, translated_summary)

        return func.HttpResponse(str(result), status_code=200)
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return func.HttpResponse("An error occurred while processing your request.", status_code=500)

def extract_text_from_url(target_url):
    """Extracts text content from the given URL using BeautifulSoup."""
    try:
        response = requests.get(target_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return ' '.join(paragraph.get_text() for paragraph in paragraphs)
    except Exception as error:
        logging.error(f"Failed to fetch or parse content from URL: {error}")
        return None

def get_text_analytics_client():
    """Initializes and returns an Azure Text Analytics client using environment variables."""
    ta_key = os.getenv('TEXT_ANALYTICS_KEY')
    ta_endpoint = os.getenv("TEXT_ANALYTICS_ENDPOINT")
    ta_credential = AzureKeyCredential(ta_key)
    return TextAnalyticsClient(endpoint=ta_endpoint, credential=ta_credential)

def summarize_and_translate(text_analytics_client, text_content):
    """Summarizes and translates the text using Azure Text Analytics and Translator APIs."""
    try:
        # Define the summary action with a maximum of 4 sentences
        summary_action = ExtractiveSummaryAction(max_sentence_count=8)
        analysis_result = text_analytics_client.begin_analyze_actions([text_content], actions=[summary_action]).result()
        summary_sentences = " ".join(sentence.text for sentence in analysis_result[0][0].sentences)

        # Get the Translator API configuration
        translator_key = os.getenv('TRANSLATOR_KEY')
        translator_endpoint = os.getenv('TRANSLATOR_ENDPOINT')
        translator_location = os.getenv('LOCATION')

        # Construct the Translator API request URL
        path = '/translate'
        constructed_url = translator_endpoint + path
        query_params = {
            'api-version': '3.0',
            'from': 'en',
            'to': 'ja'
        }

        # Set the request headers
        headers = {
            'Ocp-Apim-Subscription-Key': translator_key,
            'Ocp-Apim-Subscription-Region': translator_location,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        # Send a POST request to the Translator API
        response = requests.post(constructed_url, params=query_params, headers=headers, json=[{'text': summary_sentences}])
        translations = response.json()
        
        # Extract the translated text
        translated_texts = ''.join([translation_item['text'] for translation_response in translations for translation_item in translation_response['translations']])

        return translated_texts

    except Exception as error:
        logging.error(f"Error during summarization and translation: {error}")
        return None

def send_line_message(channel_access_token, message_text):
    """Sends a message to LINE using the LINE Messaging API."""
    line_api_url = "https://api.line.me/v2/bot/message/push"
    line_user_id = os.getenv('LINE_ID')

    # Set the appropriate headers and data payload
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}"
    }
    payload = {
        "to": line_user_id,
        "messages": [{"type": "text", "text": message_text}]
    }

    # Send the message via POST request to the LINE Messaging API
    response = requests.post(line_api_url, headers=headers, json=payload)
    return response.json()
