import os
import sys
import json
import re
from datetime import datetime
from app_utils import load_dotenv

from shiny.express import ui
from chatlas import ChatAnthropic, ChatOpenAI, ChatGoogle, ChatOllama

# Either explicitly set the OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable before launching the
# app, or set them in a file named `.env`. The `python-dotenv` package will load `.env`
# as environment variables which can later be read by `os.getenv()`.
load_dotenv()

provider = os.environ.get('QUARTO_DS_CHATBOT_PROVIDER') or 'anthropic'
model = os.environ.get('QUARTO_DS_CHATBOT_MODEL')
debug = os.environ.get('QUARTO_DS_CHATBOT_DEBUG') or False
outdir = os.environ.get('QUARTO_DS_CHATBOT_OUTPUT_DIR') or '.'

provider_greeting = ""
match provider:
    case 'anthropic':
        model = model or "claude-3-5-sonnet-20240620" # claude-3-5-sonnet-latest currently crashes
    case 'openai':
        model = model or "gpt-4o"
    case 'google':
        model = model or 'gemini-1.5-flash'
        provider_greeting = "> 🚧 Warning\\\n> `google gemini` tool calling is not quite working, but it looks like it could work. If you know how to fix this, please submit a PR.\n\n"
    case 'ollama':
        model = model or "llama3.2"
        provider_greeting = "> 🚧 Warning\\\n> `ollama` tool calling does not seem to be working, so you probably won't get Quarto document outputs yet. If you know how to fix this, please submit a PR.\n\n"
    case _:
        print('unsupported provider', provider)
        sys.exit(2)

print(f'Using provider {provider}, model {model}')
print('Output directory:', outdir)

author_name = f"{provider} {model}"

# Set up the Shiny page
ui.page_opts(
    title=ui.div(
        ui.h2("Quarto Data Science Chat"),
        ui.h6(ui.code(author_name))
    ),
    # subtitle=author_name, # 
    fillable=True,
    fillable_mobile=True,
)

system_prompt = f"""
You are a terse data science chatbot. When you are asked a question,
you will submit your answer in the form of a Quarto markdown document
including the original question, an overview, any requested code, and an explanation.
Please use the `show_answer` tool for all of your responses.
For the filename, use a five-word summary of the question, separated by
dashes and the extension .qmd
Make sure to include the Quarto metadata block at the top of the document:
* the author is "{author_name}"
* the date is {str(datetime.now())}
You don't need to add quadruple backticks around the document.
Please remember to surround the language with curly braces when outputting a code block, e.g.
```{{python}}
```{{r}}
Thank you!
"""

def show_answer(filename: str, answer: str) -> bool:
    """
    Reports an answer in Quarto markdown format.

    Parameters
    ----------
    filename
        The output filename for the Quarto document, with extension "qmd".
    answer
        The answer and explanation in Quarto markdown format.
    
    Returns
    -------
    True for success, False for failure
    """
    print('\nreceived quarto markdown result\n')
    print(answer)
    if filename:
        if not re.search(r'\.qmd$', filename):
            filename = filename + '.qmd' # choose your battles
        count = None
        while True:
            if count:
                filename2 = re.sub(r'\.qmd$', '-' + str(count) + '.qmd', filename)
            else:
                filename2 = filename
            filename2 = os.path.join(outdir, filename2)
            try:
                with open(filename2, "x") as qmd_file:
                    print('\nwrote answer to', filename2)
                    qmd_file.write(answer)
                    break
            except:
                count = (count or 1) + 1
    return True

messages = [
    {"role": "system", "content": system_prompt},
    {"content": f"Hello! I am a chatbot which responds to all questions with Quarto documents, written to \\\n`"
        + outdir + "` \n\n"
        + provider_greeting
        + "How can I help you today?", "role": "assistant"},
]
streaming = True
match provider:
    case 'anthropic':
        chat_model_constructor = ChatAnthropic
    case 'openai':
        chat_model_constructor = ChatOpenAI
    case 'google':
        chat_model_constructor = ChatGoogle
    case 'ollama':
        chat_model_constructor = ChatOllama
        streaming = False
chat_model = chat_model_constructor(system_prompt=system_prompt, model=model)
chat_model.register_tool(show_answer)
chat = ui.Chat(id="chat", messages=messages)
# Create and display empty chat
chat.ui()


# Define a callback to run when the user submits a message
@chat.on_user_submit
async def _():
    if streaming:
        response = chat_model.stream(chat.user_input(), echo = debug and "all")
#        response = await chat_model.stream_async(chat.user_input())
        await chat.append_message_stream(response)
    else:
        response = chat_model.chat(chat.user_input(), echo = debug and "all")
        await chat.append_message(response.content)

