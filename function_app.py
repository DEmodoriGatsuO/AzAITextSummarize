import azure.functions as func
import logging
import os
import requests
from bs4 import BeautifulSoup
from openai import AzureOpenAI

# Initialize the Azure OpenAI client using environment variables
openai_client = AzureOpenAI(
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_key=os.getenv('AZURE_OPENAI_KEY'),
    api_version="2024-02-15-preview"
)

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

        # Summarize and translate the extracted text
        extract_summary = extract_summary_and_analysis(extracted_text)
        if not extract_summary:
            return func.HttpResponse("Failed to generate a summary.", status_code=500)

        # Get the LINE Messaging API access token and send the extracted text
        line_channel_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        result = send_line_message(line_channel_token, url_to_summarize, extract_summary)

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

def extract_summary_and_analysis(input_text: str) -> str:
    """
    Extracts a summary and analysis from the provided text using Azure OpenAI services.

    Args:
        input_text (str): The text content to be summarized.

    Returns:
        str: A formatted string containing the summary and analysis results.
    """
    # Construct the prompt to extract "Title" and "New Features or Improvements" in Japanese
    summary_prompt = f"""
    下記の文章から「タイトル」「新機能や改善点」を抽出し、日本語で出力してください。
    ----------
    {input_text}
    """
    # Generate the summary using the specified OpenAI chat model
    summary_response = openai_client.chat.completions.create(
        model=os.getenv('AZURE_OPENAI_DEPLOY_NAME'),
        messages=[
            {"role": "system", "content": summary_prompt},
        ]
    )
    summary_result = summary_response.choices[0].message.content

    # Construct the prompt to extract "Explanation" and "Importance" in Japanese
    analysis_prompt = f"""
    下記の文章から「解説」「重要度」を抽出し、日本語で出力してください。
    ----------
    {input_text}
    """
    # Generate the analysis using the same OpenAI chat model deployment
    analysis_response = openai_client.chat.completions.create(
        model=os.getenv('AZURE_OPENAI_DEPLOY_NAME'),
        messages=[
            {"role": "system", "content": analysis_prompt},
        ]
    )
    analysis_result = analysis_response.choices[0].message.content

    # Combine the summary and analysis results into a single formatted response
    combined_results = f"{summary_result}\n{analysis_result}"
    return combined_results

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
