from typing import Callable
import gradio as gr
import os
import time
from server import process_question, process_file, conversation, start_vanilla_conversation
from config import edit_config, get_config, logger
import pathlib
import tempfile

directory = None
print(f"temp dir: {directory}")

getResponse: Callable[[str], str] = process_question

lastText = ""

def set_get_response(get_response: Callable[[str], str]):
    getResponse = get_response

def add_text(history, text):
    global lastText
    lastText = text
    history = history + [(text, None)]
    return history, gr.Textbox(value="", interactive=False)


def add_file(history, file):
    history = history + [((file.name,), None)]
    return history


def bot(history):
    global lastText
    if not (conversation and len(conversation) > 0):
        start_vanilla_conversation()
        conversation.append({"role": "user", "content": lastText})
    
    response = getResponse(lastText)
    history[-1][1] = ""
    for chunk in response:
        history[-1][1] += chunk
        yield history

last_size = 0
def get_last_response():
    global last_size
    global directory
    if(not directory):
        directory = tempfile.mkdtemp()
        print(f"temp dir: {directory}")
        logger.info(f"temp dir: {directory}")
    if(last_size != len(conversation) and conversation and conversation[-1]):
        file_name = f"conversation{time.time()}.txt"
        full_name = pathlib.Path(directory) / file_name
        print(f"calculated full name: {str(full_name)}")
        with open(str(full_name), "w") as f:
            f.write(conversation[-1]["content"])
        logger.info(f"Saved conversation to {str(full_name)}")
        last_size = len(conversation)
        return full_name._str


# Create an instance of the edit_config function
config_interface = edit_config(get_config())

latex_delimiters=[ 
              {"left": "\[", "right": "\]", "display": True},
              {"left": "\\(", "right": "\\)", "display": False},
              {"left": "$$", "right": "$$", "display": False },
              {"left": '$', "right": '$', "display": False},
              ]
# calling it demo to enable reload when calling with gradio <app> instead of python <app>
with gr.Blocks(title="AI") as demo:
    with gr.Tab(label="Chatbot"):
        gr.Interface(process_file, "files", outputs=gr.Label(label="Result of import"), title="Upload a pdf, docx or txt file", allow_flagging="never")
        chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            bubble_full_width=False,
            label="Chat with the AI",
            avatar_images=(None, (os.path.join(os.path.dirname(__file__), "logoblue.png"))),            latex_delimiters=latex_delimiters,
        )
        
        with gr.Row(variant="panel"):
            txt = gr.Textbox(
                scale=4,
                show_label=False,
                placeholder="Enter text and press enter...",
                container=False,
            )

        with gr.Row(variant="panel"):
            gr_outputs = [gr.File(label="Output File",
                                    file_count="single",
                                    file_types=[".md"])]
            gr_submit_button = gr.Button("Save last response to file", scale=0)

        gr_submit_button.click(get_last_response, None, gr_outputs)

        txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
            bot, chatbot, chatbot, api_name="bot_response"
        )
        txt_msg.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False)

    with gr.Tab("Edit Config"):
        config_interface.render()

        
    

demo.queue()
lastText = ""

demo.launch(share=True)