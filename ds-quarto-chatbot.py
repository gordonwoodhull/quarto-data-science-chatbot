# ------------------------------------------------------------------------------------
# A basic Shiny Chat example powered by Anthropic's Claude model.
# To run it, you'll need an Anthropic API key.
# To get one, follow the instructions at https://docs.anthropic.com/en/api/getting-started
# ------------------------------------------------------------------------------------
import os
import sys

from app_utils import load_dotenv
from anthropic import AsyncAnthropic

from shiny.express import ui
from openai import AsyncOpenAI

model = os.environ.get('DS_QUARTO_MODEL') or 'anthropic'

# Either explicitly set the ANTHROPIC_API_KEY environment variable before launching the
# app, or set them in a file named `.env`. The `python-dotenv` package will load `.env`
# as environment variables which can later be read by `os.getenv()`.
load_dotenv()
match model:
    case 'anthropic':
        llm = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    case 'openai':
        llm = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    case _:
        print('unsupported model', model)
        sys.exit(2)

# Set some Shiny page options
ui.page_opts(
    title="Quarto Data Science Chat (" + model + ")",
    fillable=True,
    fillable_mobile=True,
)

messages = []
match model:
    case 'anthropic':
        chat = ui.Chat(id="chat")
    case 'openai':
        chat = ui.Chat(id="chat", messages=[
            {"content": "Hello! How can I help you today?", "role": "assistant"},
        ])
# Create and display empty chat
chat.ui()


# Define a callback to run when the user submits a message
@chat.on_user_submit
async def _():
    # Get messages currently in the chat
    messages = chat.messages(format=model) # i know
    # Create a response message stream
    match model:
        case 'anthropic':
            response = await llm.messages.create(
                model="claude-3-opus-20240229",
                messages=messages,
                stream=True,
                max_tokens=1000,
            )
        case 'openai':
            response = await llm.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                stream=True,
            )
    # Append the response stream into the chat
    await chat.append_message_stream(response)
