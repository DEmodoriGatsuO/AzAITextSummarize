# Azure Function: Text Summarization and Translation via LINE Messaging API

This Azure Function app extracts, summarizes, and translates text from a given URL into Japanese using the Azure OpenAI and LINE Messaging APIs.

## Features

- **Text Extraction:** Extracts all textual content from a specified URL using BeautifulSoup.
- **Summarization and Analysis:** Summarizes the extracted text using Azure OpenAI models and provides analysis.
- **LINE Messaging API Integration:** Sends the translated summary to a LINE user via a bot.

## Prerequisites

- An **Azure subscription** with the following resources:
  - Azure OpenAI Service
- **LINE Developer Account** to set up a messaging bot.
- Python 3.7 or later.

## Setup Instructions

1. **Clone the Repository:**

   ```bash
   git clone <repository_url>
   cd <repository_name>
