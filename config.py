import json
import sys
import dotenv
import os
import gradio as gr
import logging
import json
import gc

import openai

conversation = []

def clear_conversation():
    global conversation
    conversation = []

class Config:
    def __init__(self, open_ai_api_key=None, open_ai_engine_id=None, open_ai_api_type=None, open_ai_temperature=0.5, azure_open_ai_endpoint=None, azure_open_ai_base_url=None, azure_open_ai_api_version="2024-02-15-preview", log_file="log.log", log_level="ERROR", instruction_message="You are a AI assistant, please answer questions about this file: $1", welcome_message="Hello! I'm a chatbot. I can help you with your questions. How can I help you today?", azure_doc_ai_endpoint=None, azure_doc_ai_api_version=None, azure_doc_ai_key=None, open_ai_max_tokens=800, open_ai_top_p=0.95, open_ai_frequency_penalty=0, open_ai_presence_penalty=0, gradio_share=False, gradio_port=7860, gradio_host=None):
        self.open_ai_api_key = open_ai_api_key
        self.open_ai_engine_id = open_ai_engine_id
        self.open_ai_api_type = open_ai_api_type
        self.open_ai_temperature = open_ai_temperature
        self.azure_open_ai_endpoint = azure_open_ai_endpoint
        self.azure_open_ai_base_url = azure_open_ai_base_url
        self.azure_open_ai_api_version = azure_open_ai_api_version
        self.log_file = log_file
        self.log_level = log_level
        self.instruction_message = instruction_message
        self.welcome_message = welcome_message
        self.azure_doc_ai_endpoint = azure_doc_ai_endpoint
        self.azure_doc_ai_api_version = azure_doc_ai_api_version
        self.azure_doc_ai_key = azure_doc_ai_key
        self.open_ai_max_tokens = open_ai_max_tokens
        self.open_ai_top_p = open_ai_top_p
        self.open_ai_frequency_penalty = open_ai_frequency_penalty
        self.open_ai_presence_penalty = open_ai_presence_penalty
        self.gradio_share = gradio_share
        self.gradio_port = gradio_port
        if type(gradio_port) == str:
            if gradio_port.isdigit():
                self.gradio_port = int(gradio_port)
            else:
                self.gradio_port = 7860
        self.gradio_host = gradio_host

    @classmethod
    def from_file(cls, file_path):
        # if file does not exist, return an default config
        try:
            with open(file_path, 'r') as f:
                config_dict = json.load(f)
                return cls(**config_dict)
        except FileNotFoundError:
            print(f"Config file not found: {file_path}")
            save_config(cls(), file_path)
            return cls()
    @classmethod
    def from_dict(cls, config_dict):
        return cls(**config_dict)
    
def save_config(config, file_path):
    with open(file_path, 'w') as f:
        json.dump(config.__dict__, f, indent=4)

# create a global config object and a function to get it and another to set it,
# the default config path is userconfig.json if env variable CONFIG_PATH is not set
def get_config(config_path=None):
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "userconfig.json")
    return Config.from_file(config_path)

def set_config(config, config_path=None):
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "userconfig.json")
    save_config(config, config_path)

def restart_process():
  logger.warning("Restarting the process")
  gc.collect()
  os.execl(sys.executable, sys.executable, *sys.argv)
  # it should never get here
  sys.exit(0)
  
def none_if_empty(value):
 if value == "":
    return None
 return value

def edit_config(config):
    # Define the fields
    fields = {
        "open_ai_api_key": gr.components.Textbox(label="OpenAI API Key", type="password", value=config.open_ai_api_key),
        "open_ai_engine_id": gr.components.Textbox(label="Azure Deployment Name or OpenAI Model", value=config.open_ai_engine_id, info="Use gtp-4-turbo-preview, for example"),
        "open_ai_api_type": gr.components.Dropdown(choices=['azure', 'openai'], label="OpenAI API Type", value=config.open_ai_api_type),
        "open_ai_temperature": gr.components.Slider(minimum=0, maximum=1, step=0.01, label="OpenAI Temperature", value=config.open_ai_temperature, info="Lower values are more conservative, higher values are more creative. Use 0.5 if you are unsure"),
        "azure_open_ai_endpoint": gr.components.Textbox(label="Azure/OpenAI Endpoint", value=config.azure_open_ai_endpoint, info="Leave blank"),
        "azure_open_ai_base_url": gr.components.Textbox(label="Azure/OpenAI Base URL", value=config.azure_open_ai_base_url, info="Always use https://api.openai.com/v1/chat/completions for OpenAI"),
        "azure_open_ai_api_version": gr.components.Textbox(label="Azure OpenAI API Version", value=config.azure_open_ai_api_version),
        "log_file": gr.components.Textbox(label="Log File", value=config.log_file),
        "log_level": gr.components.Dropdown(choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], label="Log Level", value=config.log_level),
        "instruction_message": gr.components.Textbox(label="Instruction Message", value=config.instruction_message, info="Use $1 to insert the text", lines=5),
        "welcome_message": gr.components.Textbox(label="Welcome Message", value=config.welcome_message),
        "azure_doc_ai_endpoint": gr.components.Textbox(label="Azure DocAI Endpoint", value=config.azure_doc_ai_endpoint, info="Azure Document AI endpoint. If blank it will use local conversion. WARNING: If Document AI instance uses free tier, only first 2 pages are converted."),
        "azure_doc_ai_api_version": gr.components.Textbox(label="Azure DocAI API Version", value=config.azure_doc_ai_api_version, info="It is not used. Leave blank"),
        "azure_doc_ai_key": gr.components.Textbox(label="Azure DocAI Key", type="password", value=config.azure_doc_ai_key, info="This is the Azure Document AI key. If it is blank it will use local conversion"),
        "open_ai_max_tokens": gr.components.Slider(minimum=0, maximum=5000, step=1, label="OpenAI Max Tokens", value=config.open_ai_max_tokens, info="Use 800 if you are unsure. Limit the number of tokens generated by OpenAI (save money and time)"),
        "open_ai_top_p": gr.components.Slider(minimum=0, maximum=1, step=0.01, label="OpenAI Top P", value=config.open_ai_top_p, info="Use 0 if using temperature (recommended). Higher values are more creative, lower values are more conservative"),
        "open_ai_frequency_penalty": gr.components.Slider(minimum=0, maximum=1, step=0.01, label="OpenAI Frequency Penalty", value=config.open_ai_frequency_penalty),
        "open_ai_presence_penalty": gr.components.Slider(minimum=0, maximum=1, step=0.01, label="OpenAI Presence Penalty", value=config.open_ai_presence_penalty),
        "gradio_share": gr.components.Checkbox(label="Share on the Internet", value=config.gradio_share, info="Check this box to make the chatbot available via the Internet. Uncheck it to make local only. Antivirus may identify it as false positive virus."),
        "gradio_port": gr.components.Textbox(label="Gradio Port", value=config.gradio_port, info="Port to run the Gradio server"),
        "gradio_host": gr.components.Textbox(label="Gradio Host", value=config.gradio_host, info="Host to run the Gradio server. You may leave blank to run locally only or 0.0.0.0 to be available to other machines in the network."),
    }



    # Define the function to update the config
    def update_config(*args):
        i=0
        configDict = {}
        for key in fields.keys():
            configDict[key] = args[i]
            if(type(args[i]) == str):
                configDict[key] = none_if_empty(args[i])
            if(key == "gradio_port"):
                if args[i] != None and args[i] != "" and args[i].isdigit():
                    configDict[key] = int(args[i])
                else:
                    configDict[key] = 7860
            if(type(args[i]) == str):
                configDict[key] = none_if_empty(args[i])
            i += 1
        
        config = Config.from_dict(configDict)
        set_config(config)
        gr.Warning("Config updated. Restarting the process. Reload the page to see the changes.")
        restart_process()

        
    
    # Create the interface
    #btn = gr.Button("Update Config (it will restart the process)", variant="primary", js="setTimeout(() =>  window.location.reload(),1000)")
    #btn.click(None, js="setTimeout(() =>  window.location.reload(),1000)")
    iface = gr.Interface(fn=update_config, inputs=list(fields.values()), outputs=None, allow_flagging="never",
                          title="Config Editor", description="Edit the config file", 
                          submit_btn="Update Config (it will restart the process)")

    
    return iface

# create logging function
def get_logger(config):
    log_level = getattr(logging, config.log_level)
    logging.basicConfig(filename=config.log_file, level=log_level)
    return logging

logger = get_logger(get_config())

if __name__ == "__main__":
    config = get_config()
    logger = get_logger(config)
    logger.info("Config loaded")
    iface = edit_config(config)
    iface.launch()