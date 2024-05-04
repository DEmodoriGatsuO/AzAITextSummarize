import azure.functions as func
import logging
import os
import requests
from bs4 import BeautifulSoup
from azure.ai.textanalytics import TextAnalyticsClient, ExtractiveSummaryAction
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

def extract_text_from_url(url):
    """Extracts text from the given URL using BeautifulSoup."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return ' '.join(p.get_text() for p in paragraphs)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def get_azure_clients():
    """Configures and returns Azure Text Analytics and OpenAI clients."""
    key = os.getenv('TEXT_ANALYTICS_KEY')
    endpoint = os.getenv("TEXT_ANALYTICS_ENDPOINT")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(endpoint=endpoint, credential=ta_credential)
    openai_client = AzureOpenAI(azure_endpoint=azure_endpoint, api_key=api_key, api_version="2024-02-15-preview")
    
    return text_analytics_client, openai_client

def summarize_and_translate(text_analytics_client, openai_client, text):
    """Summarizes and translates the text using Azure AI."""
    try:
        summary_action = ExtractiveSummaryAction(max_sentence_count=4)
        response = text_analytics_client.begin_analyze_actions([text], actions=[summary_action]).result()
        summary = " ".join(sentence.text for sentence in response[0][0].sentences)

        response = openai_client.chat.completions.create(
            model="AzAITextSummarizeGPT",
            messages=[
                {"role": "system", "content": "Please translate the provided text to Japanese and format it as a bullet list."},
                {"role": "user", "content": summary}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def send_line_message(token, message):
    """Sends a message to LINE using the LINE Messaging API."""
    url = "https://api.line.me/v2/bot/message/push"
    line_id = os.getenv('LINE_ID')
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    data = {"to": line_id, "messages": [{"type": "text", "text": message}]}
    response = requests.post(url, headers=headers, json=data)
    return response.json()

@app.route(route="AzAITextSummarize", methods=['POST'])
def AzAITextSummarize(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        data = req.get_json()
        url = data.get('url')
        if not url:
            return func.HttpResponse("Please provide a URL in the request body.", status_code=400)
        
        text = extract_text_from_url(url)
        if not text:
            return func.HttpResponse("Failed to extract text from the provided URL.", status_code=500)
        
        text_analytics_client, openai_client = get_azure_clients()
        translated_summary = summarize_and_translate(text_analytics_client, openai_client, text)
        if not translated_summary:
            return func.HttpResponse("Failed to generate translated summary.", status_code=500)
        
        # You should securely store your token in an environment variable.
        token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        result = send_line_message(token, translated_summary)
        return func.HttpResponse(str(result), status_code=200)
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return func.HttpResponse("An error occurred while processing your request.", status_code=500)
