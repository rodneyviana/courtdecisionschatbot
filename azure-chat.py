from typing import Callable
import gradio as gr
import os
import time
from server import process_question, process_file, conversation
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
    response = getResponse(lastText)
    history[-1][1] = ""
    for chunk in response:
        history[-1][1] += chunk
        yield history

last_size = 0
def get_last_response(d):
    global last_size
    global directory
    if(not directory):
        directory = tempfile.mkdtemp()
        print(f"temp dir: {directory}")
        logger.info(f"temp dir: {directory}")
    if(last_size != len(conversation) and conversation and conversation[-1]):
        last_size = len(conversation)
        file_name = f"conversation{time.time()}.txt"
        full_name = pathlib.Path(directory) / file_name
        print(f"calculated full name: {full_name._str}")
        with open(full_name._str, "w") as f:
            f.write(conversation[-1]["content"])
        logger.info(f"Saved conversation to {full_name._str}")
        return full_name._str


# Create an instance of the edit_config function
config_interface = edit_config(get_config())

# calling it demo to enable reload when calling with gradio <app> instead of python <app>
with gr.Blocks(title="AI") as demo:
    with gr.Tab(label="Chatbot"):
        gr.Interface(process_file, "files", outputs=gr.Label(label="Result of import"), title="Upload a pdf, docx or JSON file", allow_flagging="never")
        chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            bubble_full_width=False,
            label="Chat with the AI",
            avatar_images=(None, (os.path.join(os.path.dirname(__file__), "OIP.jpg"))),
            latex_delimiters=[
              {"left": '$$', "right": '$$', "display": True},
              {"left": '$', "right": '$', "display": False},
              {"left": "\(", "right": "\)", "display": False},
              {"left": "\[", "right": "\]", "display": True}
          ],
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