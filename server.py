# Import the required libraries
import gradio as gr
import pdfplumber
import json
import openai
import dotenv
import docx
from document_analysis import JudgeDecision2116278PDF
from discord.utils import escape_markdown
from config import get_config, get_logger, conversation, clear_conversation

dotenv.load_dotenv()

latex_instructions = "You are an AI ChatBot and respond all questions, you may respond using LaTeX if necessary,but you have to substitute all multiline LaTex by single line LaTex surrounded by $$ (no \\n), for example:\ninstead of returning LaTeX multiline like this:\n\\[\n\\begin{pmatrix}\n1 & 2 & 3 \\\\\na & b & c \\\\\nx & y & z\n\\end{pmatrix}\n\\]\n\nreturn a single LaTeX line like this (remove any new lines replacing \\\\\\n by \\\\\\\\ and it is indeed character '\\' repeated 4 times and no new line):\n$$ \\begin{bmatrix} 1 & 2 & 3 \\\\\\\\ a & b & c \\\\\\\\ x & y & z \\end{bmatrix} $$\n\nFor single line LaTeX do make sure to use $$ to start and $$ to end as well, so instead of returning a single line LaTeX as:\n\\( A^T \\) if \\( A \\) \n\nReturn this:\n$$ A^T $$ if $$ A $$"

logger = get_logger(get_config())

def set_get_response(s):
  pass
#markdown_bot = None

# Load the environment variables
# dotenv.load_dotenv()
# openai.api_type = os.getenv("OPENAI_API_TYPE")
# openai.api_base = os.getenv("AZURE_OPENAI_BASE_URL")
# openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
# openai.api_key = os.getenv("OPENAI_API_KEY")

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



conversation = []

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
    if files is None:
        files = []
    for file in files:
        logger.info(f"Processing file: {file.name}")
        if file is None:
            continue  # Skip if the file is None
        text = ""
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
        if text:
            texts.append(text)
        
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

def process_question(question: str):
  global conversation
  # Use OpenAI to create a chat based on the text
  # Set the engine and the temperature
  if(question is None or len(question) == 0):
    return "Please enter a question."
  # engine = os.getenv("OPENAI_ENGINE_ID") or "davinci"
  # temperature = float(os.getenv("OPENAI_TEMPERATURE") or 0.5)
  # Create a prompt with the text and a question
  #prompt = f"The following is a court decision:\n{document_text}\n\nQ: "
  # Use gr.Interface to create a chat interface
  conversation.append({
      "role": "user",
      "content": question
    })

  completion = openai.chat.completions.create(
        model=config.open_ai_engine_id,
        messages = conversation,
        temperature=config.open_ai_temperature,
        max_tokens=config.open_ai_max_tokens,
        top_p=config.open_ai_top_p,
        frequency_penalty=config.open_ai_frequency_penalty,
        presence_penalty=config.open_ai_presence_penalty,
        stream=True,
        stop=None
      )
  content = ""
  role = "assistant"
  for chunk in completion:
    if len(chunk.choices)  > 0:
      try:
        if(chunk.choices[0].delta.content is None):
          continue;
        if(chunk.choices[0].finish_reason == "length" or chunk.choices[0].finish_reason == "content_filter"):
          content = content + f" (error reason: {chunk.choices[0].finish_reason})"
          print(f"stop reason: {chunk.choices[0].finish_reason}")
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
  conversation.append({
      "role": role,
      "content": content
    })
  yield ""
  
# Create a gradio app to upload the file and process it
app = gr.Interface(
  # Define the function to process the file
  fn = process_file,
  # Define the input and output components
  inputs = gr.File(label="Upload a court decision pdf or json file"),
  outputs = "text",
  # Define the title and the description
  title = "Court Decision Chat",
  description = "This is a gradio app that allows you to upload a court decision pdf or json file and create an OpenAI chat based on it. You can ask questions about the court decision and get answers from OpenAI."
)
# Launch the app
#app.launch()

if __name__ == "__main__":
    app.launch(show_api=True, share=True)   