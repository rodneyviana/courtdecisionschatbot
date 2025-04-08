# Import the required libraries
import gradio as gr
import pdfplumber
import json
import openai
from openai.types.chat import ChatCompletionChunk
from openai.types import CompletionUsage
import dotenv
import docx
from document_ai import analyze_read
from document_analysis import JudgeDecision2116278PDF
from discord.utils import escape_markdown
from config import get_config, get_logger, conversation, clear_conversation, none_if_empty

dotenv.load_dotenv()

latex_instructions = "You are an AI ChatBot and respond all questions, you may respond using LaTeX if necessary,but you have to substitute all multiline LaTex by single line LaTex surrounded by $$ (no \\n), for example:\r\ninstead of returning LaTeX multiline like this:\r\n\\[\r\n\\begin{pmatrix}\r\n1 & 2 & 3 \\\\\r\na & b & c \\\\\r\nx & y & z\r\n\\end{pmatrix}\r\n\\]\r\n\r\nreturn a single LaTeX line like this (remove any new lines replacing \\\\\\n by \\\\\\\\ and, to be clear, it is indeed the character \'\\\' repeated 4 times and no new line \\n):\r\n$$ \\begin{bmatrix} 1 & 2 & 3 \\\\\\\\ a & b & c \\\\\\\\ x & y & z \\end{bmatrix} $$\r\n\r\nFor single line LaTeX do make sure to use $$ to start and $$ as starting and ending as the examples below.\r\nInstead of:\r\n\\( A^T \\) if \\( A \\) \r\n\r\nReturn this:\r\n$$ A^T $$ if $$ A $$\r\n\r\nInstead of:\r\n$ \\beta_2 $ is the exponential decay rate for the second moment estimates (typically set to 0.999)\r\n\r\nReturn this:\r\n$$ \\beta_2 $$ is the exponential decay rate for the second moment estimates (typically set to 0.999)"

logger = get_logger(get_config())

def set_get_response(s):
  pass

config = get_config()
openai.api_key = config.open_ai_api_key
openai.api_type = config.open_ai_api_type
openai.api_version = config.azure_open_ai_api_version
if(config.open_ai_api_type == "azure"):
  openai.azure_endpoint = config.azure_open_ai_base_url
  openai.api_base = config.azure_open_ai_base_url
  openai.base_url = None
else:
  openai.azure_endpoint = None
  openai.api_base = config.azure_open_ai_base_url


last_chatcompletion: CompletionUsage = {
  "completion_tokens": 0,
  "prompt_tokens": 0,
  "total_tokens": 0
}
conversation = []

def reset_last_chatcompletion():
   global last_chatcompletion
   last_chatcompletion = {
    "completion_tokens": 0,
    "prompt_tokens": 0,
    "total_tokens": 0
   }




def get_last_chatcompletion():
   try:
     return f"[Response Tokens: {last_chatcompletion.completion_tokens:>20,}], [Prompt Tokens: {last_chatcompletion.prompt_tokens:>20,}],  [Total Tokens: {last_chatcompletion.total_tokens:>20,}]"
   except Exception as e:
      logger.error(e)
      print(e)
      return f"Error getting tokens: {e}"

document_text = ""

def process_json(json_file: str):
    logger.info(f"Processing json file: {json_file}")
    docana: JudgeDecision2116278PDF = None
    with open(json_file, "r", encoding='utf-8') as raw_json:
      temp = json.load(raw_json) #, object_hook=JudgeDecision2116278PDF);
      docana = JudgeDecision2116278PDF(temp)
      fullText = ""
      for paragraph in docana.analyzeResult['paragraphs']:
        fullText = f"{fullText}\n{paragraph['content']}"
      document_text = fullText
      return fullText

# code to process the uploaded MS Word file to string
def process_word(file):
  # Check the file type and extract the text
  logger.info(f"Processing word file: {file}")
  if(file is None):
    return "Please upload a file."
  if file.name.endswith(".docx"):
    # Use docx to read the docx file
    doc = docx.Document(file)
    text = ""
    # Loop through the paragraphs and append the text
    for para in doc.paragraphs:
      text += para.text
  else:
    # Return an error message if the file type is not supported
    return "Sorry, I can only process docx files."
  return text

def start_vanilla_conversation(isEmpty = False):
  global conversation
  conversation.clear()
  if(isEmpty):
    conversation.append({"role": "system", "content": "You are an AI Chatbot that answers questions"})
  else:
    conversation.append({"role": "system", "content": latex_instructions})
  set_get_response(process_question)
  return "Your chat is ready. Please enter your question in the textbox below."

# Define the function to process the uploaded file and create an OpenAI chat
def process_file(files):
    global conversation
    texts = []
    totalSize = 0
    if files is None:
        files = []
    for file in files:
        logger.info(f"Processing file: {file.name}")
        print(f"Processing file: {file.name}")
        if file is None:
            continue  # Skip if the file is None
        text = ""
        if not (none_if_empty(config.azure_doc_ai_endpoint) and none_if_empty(config.azure_doc_ai_key)) or file.name.endswith(".txt"):
          logger.info("No OpenAI API key or engine ID provided or document is txt. Using local conversion.")
          print("No OpenAI API key or engine ID provided. Using local conversion.")
          if file.name.endswith(".pdf"):
              # Use pdfplumber to read the pdf file
              with pdfplumber.open(file) as pdf:
                  text = ''.join(page.extract_text() for page in pdf.pages if page.extract_text())
          elif file.name.endswith(".json"):
              # Use json to load the json file
              text = process_json(file)
          elif file.name.endswith(".docx"):
              # Use docx to read the docx file
              text = process_word(file)
          else:
              # Log an error message if the file type is not supported
              logger.error("Unsupported file type. Can only process docx, pdf, or json files. Assumint it is text")
              with open(file, "r") as f:
                  text = f.read()
        else:
          logger.info("Using Azure Doc AI to convert the file.")
          print("Using Azure Doc AI to convert the file.")
          try:
            text = analyze_read(file)
          except Exception as e:
            logger.error(e)
            gr.Error(f"Error processing file: {e}")
            print(f"Error processing file: {e}")
        if text:
            print(f"Size: {len(text)}")
            totalSize += len(text)
            print(f"Total size: {totalSize}")
            texts.append(text)
        else:
            logger.error(f"Could not process file: {file.name}")
            gr.Warning(f"Could not process file: {file.name}. Skipping.")
    instruction_message = config.instruction_message
    for i, text in enumerate(texts, start=1):
        placeholder = f"${i}"
        instruction_message = instruction_message.replace(placeholder, text)
    
    logger.info(f"Restarting conversation with instruction message: {instruction_message[:100]}")
    conversation.clear()
    #conversation.append({"role": "system", "content": latex_instructions})
    conversation.append({"role": "system", "content": instruction_message})
    set_get_response(process_question)
  
    return "Your chat is ready. Please enter your question in the textbox below."

def process_question(question: str, message_object = None):
  global conversation
  global last_chatcompletion
  if(message_object is None):
    if(question is None or len(question) == 0):
      return "Please enter a question."
    else:
      conversation.append({
          "role": "user",
          "content": question
        })
  else:
    conversation.append(message_object)
  completion: openai.Stream[ChatCompletionChunk] = openai.chat.completions.create(
        model=config.open_ai_engine_id,
        messages = conversation,
        temperature=config.open_ai_temperature,
        max_tokens=config.open_ai_max_tokens,
        top_p=config.open_ai_top_p,
        frequency_penalty=config.open_ai_frequency_penalty,
        presence_penalty=config.open_ai_presence_penalty,
        stream=(message_object is None),
        stream_options=None if message_object else {
            "include_usage": True
        },           
        stop=None
      )
  content = ""
  role = "assistant"
  if message_object:
     #yield ""
     content = completion.choices[0].message.content
     yield content
  else:
    for chunk in completion:
      if chunk.usage:
        print(f"usage: {chunk.usage}")
        logger.info(f"usage: {chunk.usage}")
        last_chatcompletion = chunk.usage
      if len(chunk.choices)  > 0:
        try:
          if(chunk.choices[0].delta is None or chunk.choices[0].delta.content is None):
            print("No content")
            logger.error("No content")
            continue;
          if(chunk.choices[0].finish_reason == "length" or chunk.choices[0].finish_reason == "content_filter"):
            content = content + f" (error reason: {chunk.choices[0].finish_reason})"
            print(f"stop reason: {chunk.choices[0].finish_reason}")
            logger.error(f"stop reason: {chunk.choices[0].finish_reason}")
            yield f" (error reason: {chunk.choices[0].finish_reason})"
            break
          content = content + chunk.choices[0].delta.content
          # role = chunk.choices[0].delta.role;
          yield chunk.choices[0].delta.content
        except Exception as e:
          logger.error(e)
          print(e)
  if(content is None or len(content) == 0):
    content = "Sorry, I could not generate a response. Please try again."
    logger.error("No content generated")
  conversation.append({
      "role": role,
      "content": content
    })
  yield ""


if __name__ == "__main__":
    print("Please run the azure-chat.py file instead of this file.")  