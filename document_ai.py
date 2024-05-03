
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from config import get_config, get_logger
import gradio as gr

"""
Remember to remove the key from your code when you're done, and never post it publicly. For production, use
secure methods to store and access your credentials. For more information, see 
https://docs.microsoft.com/en-us/azure/cognitive-services/cognitive-services-security?tabs=command-line%2Ccsharp#environment-variables-and-application-configuration
"""

def analyze_read(file_path=None):
    config = get_config()
    logger = get_logger(config)
    if(file_path is None):
        logger.error("No file path provided")
        gr.Information("Please upload a file. No conversion done.")
        return "**Error** Please upload a file."
    
    endpoint = config.azure_doc_ai_endpoint
    key = config.azure_doc_ai_key


    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key),
    )
    # Read the file into memory
    with open(file_path, "rb") as document:
        doc_content = document.read()

    # create a poller to read the document from file_path
    
    poller = document_analysis_client.begin_analyze_document("prebuilt-document", doc_content)
    result = poller.result()
    logger.info(f"Document page count: {len(result.pages)} Size: {len(result.content)} bytes")
    print(f"Document page count: {len(result.pages)} Size: {len(result.content)} bytes")
    json.dump(result.to_dict(), open("result.json", "w"), indent=4)
    return result.content

if __name__ == "__main__":
    print("run python azure-chat.py to start the chatbot.")
