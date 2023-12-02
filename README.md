## Proof of Concept of the use of ChatGPT as a legal scholar ##

You should not get the responses as professional legal advice. It is rather a assistant that can read the document and find details you would be to bother to notice after reading hundreds of pages.

I am including a public record random court document PDF that I found by Bing'ing ```"judge decision type:.pdf"```, if somehow I am not supposed to use this public record, let me know and I remove from the repository.


These are some questions I used:

- What is this document about?
- Who are the judges?
- can you make this as a table? (*)
- Can I use this opinion as precedent moving forward?
- With this decision, new restaurant owners can install natural gas?
- What are the options to natural gas?

\*  Note: this was after they gave me the names

There are two versions depending of your preference:

- **legalchat.py:** console application already tuned to use the examples I provided
- **markdown_bot.py** gradio application presenting a more interesting and interactive 

### How to run ###

1. Create a venv enviroment and install the requirements
```
python3 -m venv venv/
source ./venv/bin/activate
pip install -r requirements.txt
```

2. Create a .env file to put your environment settings. Those are:

```
OPENAI_API_KEY="<your key>"
OPENAI_ENGINE_ID="<name of your deployment>"
OPENAI_API_TYPE="azure"
OPENAI_TEMPERATURE="0.5"
AZURE_OPENAI_ENDPOINT="https://rviana-opepai-eastus2.openai.azure.com/"
AZURE_OPENAI_BASE_URL="https://rviana-opepai-eastus2.openai.azure.com/"
LOG_FILE="log.txt"
OPENAI_MAX_TOKENS="4000"
```
Temperature less the 0.5 will make it less imaginative but more precise, more than 0.7 may lead to "allucinations". I left my endpoints so you will now what to add if you look at your deployments.

3. Run you favorite flavor of the application

For console only:
```
source ./venv/bin/activate
python legalchat.py
```

For gradio (web application):
```
source ./venv/bin/activate
python legalchat.py
```
