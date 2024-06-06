import frappe
from frappe import _
import openai
import json
from erpnext_chatgpt.tools import get_tools, available_functions

# Define a pre-prompt to set the context or provide specific instructions
PRE_PROMPT = "You are an AI assistant integrated with ERPNext. Please provide accurate and helpful responses based on the following questions and data provided by the user."

@frappe.whitelist()
def ask_openai_question(conversation):
    api_key = frappe.db.get_single_value("OpenAI Settings", "api_key")
    if not api_key:
        return {"error": "OpenAI API key is not set in OpenAI Settings."}

    openai.api_key = api_key

    client = openai.Client(api_key=api_key)

    # Add the pre-prompt as the initial message
    conversation.insert(0, {"role": "system", "content": PRE_PROMPT})

    try:
        tools = get_tools()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            conversation.append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(**function_args)

                conversation.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

            second_response = client.chat.completions.create(
                model="gpt-4",
                messages=conversation
            )

            return second_response

        return {"error": "No function called"}
    except Exception as e:
        frappe.log_error(message=str(e), title="OpenAI API Error")
        return {"error": str(e)}

@frappe.whitelist()
def test_openai_api_key(api_key):
    try:
        openai.api_key = api_key
        openai.Engine.list()  # Test API call
        return True
    except Exception as e:
        frappe.log_error(message=str(e), title="OpenAI API Key Test Failed")
        return False
