import os
import requests
from bs4 import BeautifulSoup
from azure.ai.textanalytics import (
    TextAnalyticsClient,
    ExtractiveSummaryAction
) 
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

def extract_text_from_url(url):
    try:
        # Get HTML from URL
        response = requests.get(url)
        # HTTP Error Check
        response.raise_for_status()
        # HTMLをBeautifulSoupで解析
        soup = BeautifulSoup(response.text, 'html.parser')
        # <p>タグ内のテキストを抽出して連結
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        return text
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def summarize_and_translate(url):
    extracted_text = extract_text_from_url(url)
    if not extracted_text:
        return None
    
    try:
        # Language Credential
        key = os.environ.get('TEXT_ANALYTICS_KEY')
        endpoint = os.getenv("TEXT_ANALYTICS_ENDPOINT")
        ta_credential = AzureKeyCredential(key)
        text_analytics_client = TextAnalyticsClient(endpoint=endpoint, credential=ta_credential)
        
        # OpenAI Credential
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        openai_client = AzureOpenAI(azure_endpoint=azure_endpoint, api_key=api_key, api_version="2024-02-15-preview")
        
        # Text Summarization
        response = text_analytics_client.begin_analyze_actions([extracted_text], actions=[ExtractiveSummaryAction(max_sentence_count=4)])

        for result in response.result():
            # first document, first result
            extract_summary_result = result[0] 
            summary = " ".join([sentence.text for sentence in extract_summary_result.sentences])
        
        # Translation and Formatting
        response = openai_client.chat.completions.create(
            model="AzAITextSummarizeGPT",
            messages=[
                {"role": "system", "content": "Please translate the provided text to Japanese and format it as a bullet list."},
                {"role": "user", "content": summary}
            ]
        )
        
        return response.choices[0].message.content

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Main
def main(url):
    translated_summary = summarize_and_translate(url)
    if translated_summary:
        print(translated_summary)
    else:
        print("Failed to generate translated summary.")

# URLを指定して関数を呼び出し
url = 'https://powerapps.microsoft.com/en-us/blog/whats-new-power-apps-march-2024-feature-update/'
main(url)