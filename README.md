# Azure Function: Text Summarization and Translation via LINE Messaging API

This Azure Function app allows you to summarize text from a provided URL, translate the summary into Japanese, and send it via the LINE Messaging API.

## Features

- **Text Extraction:** Extracts all textual content from a specified URL using BeautifulSoup.
- **Summarization:** Summarizes the extracted text using Azure's Text Analytics Extractive Summary feature.
- **Translation:** Translates the summary into Japanese using the Azure Translator API.
- **LINE Messaging API Integration:** Sends the translated summary to a LINE user via a bot.

## Prerequisites

- An **Azure subscription** with the following resources:
  - Azure Text Analytics API
  - Azure Translator API
- **LINE Developer Account** to set up a messaging bot.
- Python 3.7 or later.

## Setup Instructions

1. **Clone the Repository:**

   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

2. **Install Dependencies:**
   Create a virtual environment and install the required dependencies.

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**

   Set up environment variables required for the Azure and LINE services.

   - `TEXT_ANALYTICS_KEY`: Your Azure Text Analytics API key.
   - `TEXT_ANALYTICS_ENDPOINT`: Endpoint URL of your Text Analytics resource.
   - `TRANSLATOR_KEY`: Your Azure Translator API key.
   - `TRANSLATOR_ENDPOINT`: Endpoint URL of your Translator resource.
   - `LOCATION`: The region associated with your Azure Translator API key.
   - `LINE_CHANNEL_ACCESS_TOKEN`: Your LINE bot's access token.
   - `LINE_ID`: The recipient's LINE ID.

   You can store these variables in a `.env` file or directly within the Azure Function app settings.

4. **Deploy the Function:**

   Follow the [Azure Function Deployment Guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-python) to deploy this function to your Azure account.

5. **Testing:**

   Use an HTTP client like Postman or cURL to send a POST request to your deployed function with a payload like this:

   ```json
   {
       "url": "https://example.com/article"
   }
   ```

## Usage

1. The function expects a POST request containing a JSON object with a single key, `url`.
2. Once triggered, the function will summarize the text found at the given URL, translate it to Japanese, and then send the translated summary to the specified LINE user.

## Troubleshooting

- Ensure all necessary environment variables are set and correct.
- Check logs in the Azure Portal for any runtime issues.
- Validate that your Azure Cognitive Services resources are active and that the API keys are not expired.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.