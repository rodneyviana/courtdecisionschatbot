#!/usr/bin/env python
import base64
from typing import Callable
import gradio as gr
import os
import time
from server import process_question, process_file, conversation, start_vanilla_conversation
from config import edit_config, get_config, logger, restart_process
import pathlib
import tempfile

appInfo = None
local_url = None
share_url = None
directory = None
print(f"temp dir: {directory}")

getResponse: Callable[[str, any], str] = process_question

config = get_config()

lastText = ""
lastMedia = None
def set_get_response(get_response: Callable[[str], str]):
    getResponse = get_response

def add_text(history, text):
    global lastText
    lastText = text
    history = history + [(text, None)]
    return history, gr.Textbox(value="", interactive=False)

# Open the image file and encode it as a base64 string
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def get_file_extension(file_name):
    return file_name.split(".")[-1]

def add_file(history, file):
    history = history + [((file.name,), None)]
    return history

def restart_chatbot(chatbot: gr.Chatbot):
    print(chatbot)
    chatbot = [(None, "New conversation started")]
    start_vanilla_conversation()
    gr.Warning("Chatbot restarted. Please refresh the page to start a new conversation.")
    return chatbot

def add_multimedia(history, file):
    if not (conversation and len(conversation) > 0):
        start_vanilla_conversation()
    global lastMedia
    file_type = "image"
    if file.name.endswith(".wav") or file.name.endswith(".wmv") or file.name.endswith(".mp3"):
        file_type = "audio"
    elif file.name.endswith(".mp4") or file.name.endswith(".mov") or file.name.endswith(".avi"):
        file_type = "video"
    base64_muiltimedia = encode_image(file.name)
    file_ext = get_file_extension(file.name)
    instr_media = f"Please see the attached {file_type} file. You will answer questions based on this {file_type} when asked. Let me know you understand by typing 'I understand'."
    message= {
        "role": "user",
        "content": [
            {
                "type": f"{file_type}_url",
                 f"{file_type}_url": {
                    "url": f"data:{file_type}/{file_ext};base64,{base64_muiltimedia}"
                }
            },
            {
                "type": "text",
                "text": instr_media
            }
          ]
        }

    history = history + [((file.name,), None)]
    history = history + [[instr_media, ""]]    
    response = getResponse(None, message)
    
    for chunk in response:
        print(f"chunk: {chunk}")
        history[-1][1] += chunk
        yield history




def bot(history):
    global lastText
    if not (conversation and len(conversation) > 0):
        start_vanilla_conversation()
        # conversation.append({"role": "user", "content": lastText})
    
    response = getResponse(lastText)
    history[-1][1] = ""
    for chunk in response:
        history[-1][1] += chunk
        yield history

last_size = 0
def get_last_response(check_save_all: gr.Checkbox):
    global last_size
    global directory
    if(not directory):
        directory = tempfile.mkdtemp()
        print(f"temp dir: {directory}")
        logger.info(f"temp dir: {directory}")
    if(conversation and conversation[-1]):
        file_name = f"conversation{time.time()}.txt"
        full_name = pathlib.Path(directory) / file_name
        print(f"calculated full name: {str(full_name)}")
        if(check_save_all):
            for i, item in enumerate(conversation):
                with open(str(full_name), "a") as f:
                    content = item["content"]
                    if isinstance(content, list):
                        for sub_item in content:
                            if sub_item["type"] == "image_url":
                                f.write(f"\n### {item['role']}:\n\n![image]({sub_item['image_url']['url']})\n")
                            else:
                                f.write(f"\n### {item['role']}:\n\n{sub_item['text']}\n")
                    else:
                        f.write(f"\n### {item['role']}:\n\n{item['content']}\n")
            last_size = len(conversation)
            return full_name._str
        else:
            with open(str(full_name), "w") as f:
                f.write(conversation[-1]["content"])
            logger.info(f"Saved conversation to {str(full_name)}")
            last_size = len(conversation)
            return full_name._str

def show_urls():
    global local_url, share_url
    gr.Info(f"Local URL: {local_url}")
    gr.Info(f"Share URL: {share_url}")
    # return f"Local URL: {local_url}\nShare URL: {share_url}"

def full_path_of_local_file(file_name):
    return os.path.join(os.path.dirname(__file__), file_name)

# Create an instance of the edit_config function
config_interface = edit_config(get_config())

latex_delimiters=[ 
              {"left": "$$", "right": "$$", "display": False },
              {"left": '$', "right": '$', "display": False},
              {"left": "\\[", "right": "\\]", "display": False},
              {"left": "\\(", "right": "\\)", "display": False},
              ]

css = """
.chatbot-container {
    background: linear-gradient(90deg, rgb(239, 242, 247) 0%, 7.60286%, rgb(237, 240, 249) 15.2057%, 20.7513%, rgb(235, 239, 248) 26.297%, 27.6386%, rgb(235, 239, 248) 28.9803%, 38.2826%, rgb(231, 237, 249) 47.585%, 48.1216%, rgb(230, 236, 250) 48.6583%, 53.1306%, rgb(228, 236, 249) 57.6029%, 61.5385%, rgb(227, 234, 250) 65.4741%, 68.7835%, rgb(222, 234, 250) 72.093%, 75.7603%, rgb(219, 230, 248) 79.4275%, 82.8265%, rgb(216, 229, 248) 86.2254%, 87.8354%, rgb(213, 228, 249) 89.4454%, 91.8605%, rgb(210, 226, 249) 94.2755%, 95.4383%, rgb(209, 225, 248) 96.6011%, 98.3005%, rgb(208, 224, 247) 100%);
}
"""

NORMAL_BORDER_COLOR = "#C0C0C0" # '*body_text_color'
theme = gr.themes.Soft().set(
    #border_color_accent='*body_text_color',
    border_color_primary= NORMAL_BORDER_COLOR,
    checkbox_border_color= NORMAL_BORDER_COLOR,
    input_border_color= NORMAL_BORDER_COLOR,
    input_border_width='1px',
    button_border_width='*panel_border_width',
    button_border_width_dark='*panel_border_width',
    button_primary_border_color= NORMAL_BORDER_COLOR,
    button_secondary_border_color= NORMAL_BORDER_COLOR
)

# calling it demo to enable reload when calling with gradio <app> instead of python <app>
with gr.Blocks(title="AI", theme=theme, css=css) as demo:
    with gr.Tab(label="Chatbot"):
        gr.Interface(process_file, "files", 
                     outputs=gr.Label(label="Result of import"),
                     title="Upload a pdf, docx or txt file",
                     allow_flagging="never",
                     )
        chatbot = gr.Chatbot(
            [(None, config.welcome_message)],
            elem_id="chatbot",
            bubble_full_width=False,
            label="Chat with the AI",
            avatar_images=(full_path_of_local_file("userlogo.png"), full_path_of_local_file("botlogo.png")),
            elem_classes="chatbot-container",
            latex_delimiters=latex_delimiters,
            show_copy_button=True,

            
        )
        
        with gr.Row(variant="panel"):
            
            txt = gr.Textbox(
                scale=4,
                show_label=False,
                placeholder="Enter text and press enter...",
                container=False,
            )
            btn = gr.UploadButton("📁", file_types=["image", "video", "audio"])

        with gr.Row(variant="panel"):
            gr_check_save_all = gr.Checkbox(label="Save all responses", value=False, scale=0)
            gr_outputs = [gr.File(label="Output File",
                                    file_count="single",
                                    file_types=[".md"])]
            gr_submit_button = gr.Button("Save last response to file", scale=0)

        gr_submit_button.click(get_last_response, gr_check_save_all, gr_outputs)

        txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
            bot, chatbot, chatbot, api_name="bot_response"
        )
        txt_msg.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False)
        file_msg = btn.upload(add_multimedia, [chatbot, btn], [chatbot], queue=False) #.then(
        # bot, chatbot, chatbot, api_name="bot_response"
        # )
        with gr.Row():
            show_url_btn = gr.Button("Show URLs", scale=0)
            restart_chatbot_btn = gr.Button("Restart Conversation", scale=0)
            restart_btn = gr.Button("Restart Application", scale=0)
            restart_chatbot_btn.click(restart_chatbot, chatbot, chatbot)
            restart_btn.click(restart_process)
            show_url_btn.click(show_urls)
    with gr.Tab("Edit Config"):
        config_interface.render()

        
    

demo.queue()
lastText = ""

apiInfo, local_url, share_url = demo.launch(share=config.gradio_share, server_port=config.gradio_port, server_name=config.gradio_host, prevent_thread_lock=True)
logger.info(f"Launched interface with info: {apiInfo}")
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Shutting down the server...")

