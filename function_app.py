import azure.functions as func
import logging
import os
import uuid
import requests
from bs4 import BeautifulSoup
from azure.ai.textanalytics import TextAnalyticsClient, ExtractiveSummaryAction
from azure.core.credentials import AzureKeyCredential

# Initialize the Azure Function App with specific HTTP authentication level
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="AzLINETextSummarization", methods=['POST'])
def az_ai_text_summarize(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function to summarize and translate text from a URL, and send it via LINE Messaging API."""
    logging.info('Processing the HTTP request in Python Azure Function.')

    try:
        # Extract the JSON data from the incoming request
        data = req.get_json()
        url_to_summarize = data.get('url')
        
        # Validate that a URL has been provided in the request body
        if not url_to_summarize:
            return func.HttpResponse("Please provide a URL in the request body.", status_code=400)
        
        # Extract text from the specified URL using BeautifulSoup
        extracted_text = extract_text_from_url(url_to_summarize)
        if not extracted_text:
            return func.HttpResponse("Failed to extract text from the provided URL.", status_code=500)

        # Retrieve Azure Text Analytics client
        text_analytics_client = get_text_analytics_client()

        # Summarize and translate the extracted text
        translated_summary = summarize_and_translate(text_analytics_client, extracted_text)
        if not translated_summary:
            return func.HttpResponse("Failed to generate a translated summary.", status_code=500)

        # Get the LINE Messaging API access token and send the translated summary
        line_channel_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        result = send_line_message(line_channel_token, url_to_summarize, translated_summary)

        return func.HttpResponse(str(result), status_code=200)
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return func.HttpResponse("An error occurred while processing your request.", status_code=500)

def extract_text_from_url(target_url):
    """Extracts text content from the given URL using BeautifulSoup."""
    try:
        # Send an HTTP GET request to the provided URL and verify status
        response = requests.get(target_url)
        response.raise_for_status()

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')

        # Return all text found within paragraph tags, joined as a single string
        return ' '.join(paragraph.get_text() for paragraph in paragraphs)
    except Exception as error:
        logging.error(f"Failed to fetch or parse content from URL: {error}")
        return None

def get_text_analytics_client():
    """Initializes and returns an Azure Text Analytics client using environment variables."""
    # Retrieve Text Analytics credentials from environment variables
    ta_key = os.getenv('TEXT_ANALYTICS_KEY')
    ta_endpoint = os.getenv("TEXT_ANALYTICS_ENDPOINT")
    
    # Create a credential object and initialize the Text Analytics client
    ta_credential = AzureKeyCredential(ta_key)
    return TextAnalyticsClient(endpoint=ta_endpoint, credential=ta_credential)

def summarize_and_translate(text_analytics_client, text_content):
    """Summarizes and translates the text using Azure Text Analytics and Translator APIs."""
    try:
        # Define the summary action with a specified maximum sentence count
        summary_action = ExtractiveSummaryAction(max_sentence_count=4)

        # Start the analysis and wait for the results
        analysis_result_paged = text_analytics_client.begin_analyze_actions(
            [text_content], actions=[summary_action]
        ).result()

        # Initialize a list to collect all summary sentences
        summary_sentences = []

        # Iterate over pages of analysis results and collect summary sentences
        for result_page in analysis_result_paged:
            for extractive_summary_result in result_page:
                if hasattr(extractive_summary_result, "sentences"):
                    summary_sentences.extend(
                        sentence.text for sentence in extractive_summary_result.sentences
                    )
                else:
                    logging.error("Error during action execution.")

        # Join the collected sentences to form a cohesive summary
        summary = " ".join(summary_sentences)

        # Retrieve Translator API credentials and endpoints
        translator_key = os.getenv('TRANSLATOR_KEY')
        translator_endpoint = os.getenv('TRANSLATOR_ENDPOINT')
        translator_location = os.getenv('LOCATION')

        # Set the URL path and parameters for the Translator API
        path = '/translate'
        constructed_url = translator_endpoint + path
        query_params = {
            'api-version': '3.0',
            'from': 'en',
            'to': 'ja'
        }

        # Set up request headers including unique trace ID
        headers = {
            'Ocp-Apim-Subscription-Key': translator_key,
            'Ocp-Apim-Subscription-Region': translator_location,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        # Send the POST request to the Translator API and collect translations
        response = requests.post(constructed_url, params=query_params, headers=headers, json=[{'text': summary}])
        translations = response.json()

        # Extract and join the translated texts
        translated_texts = ''.join([translation_item['text'] for translation_response in translations for translation_item in translation_response['translations']])

        return translated_texts

    except Exception as error:
        logging.error(f"Error during summarization and translation: {error}")
        return None

def send_line_message(channel_access_token, url_to_summarize, message_text):
    """Sends a message to LINE using the LINE Messaging API."""
    # Retrieve LINE Messaging API URL and user ID from environment variables
    line_api_url = "https://api.line.me/v2/bot/message/push"
    line_user_id = os.getenv('LINE_ID')

    # Prepare the request headers and payload for the initial URL message
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}"
    }
    payload_url = {
        "to": line_user_id,
        "messages": [{"type": "text", "text": url_to_summarize}]
    }

    # Send the URL message to the LINE API
    requests.post(line_api_url, headers=headers, json=payload_url)

    # Prepare the request payload for the translated summary message
    payload_summary = {
        "to": line_user_id,
        "messages": [{"type": "text", "text": message_text}]
    }

    # Send the summary message to the LINE API and return the response JSON
    response = requests.post(line_api_url, headers=headers, json=payload_summary)
    return response.json()
