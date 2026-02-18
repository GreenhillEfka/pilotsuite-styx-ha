"""
OpenAI-Compatible Conversation API for Extended OpenAI Conversation

Provides /v1/chat/completions endpoint compatible with:
- Extended OpenAI Conversation (HA custom component)
- OpenAI SDK
- Any OpenAI-compatible client

Features:
- Function calling for HA services
- Streaming support
- Conversation context
"""

from flask import Blueprint, request, jsonify
import logging
import json
import os

logger = logging.getLogger(__name__)

conversation_bp = Blueprint('conversation', __name__, url_prefix='/chat')

# HA Service function definitions for function calling
HA_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "execute_services",
            "description": "Execute Home Assistant services to control devices",
            "parameters": {
                "type": "object",
                "properties": {
                    "list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": "The domain of the service (e.g., light, switch, climate)"
                                },
                                "service": {
                                    "type": "string",
                                    "description": "The service to call (e.g., turn_on, turn_off)"
                                },
                                "service_data": {
                                    "type": "object",
                                    "description": "Data to pass to the service",
                                    "properties": {
                                        "entity_id": {
                                            "type": "string",
                                            "description": "The entity_id to control"
                                        }
                                    }
                                }
                            },
                            "required": ["domain", "service", "service_data"]
                        }
                    }
                },
                "required": ["list"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_states",
            "description": "Get the current state of Home Assistant entities",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain (e.g., light, sensor)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_history",
            "description": "Get history of entities",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entity IDs"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time (ISO format)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time (ISO format)"
                    }
                }
            }
        }
    }
]

# System prompt for Home Assistant conversation
HA_SYSTEM_PROMPT = """You are a helpful Home Assistant assistant. You can control devices in the home through Home Assistant services.

You have access to these functions:
- execute_services: Call Home Assistant services to control devices
- get_states: Get current state of entities
- get_history: Get historical data

When a user asks to control a device (like "turn on the light"), use the execute_services function.
When you need to know the current state of something, use get_states.
When you need historical information, use get_history.

Be concise and helpful. Confirm actions after executing them."""


@conversation_bp.route('/completions', methods=['POST'])
def chat_completions():
    """
    OpenAI-compatible chat completions endpoint
    
    Expected payload (OpenAI format):
    {
        "model": "gpt-4" (or any string, we use our own),
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ],
        "functions": [...],  # optional
        "stream": false     # or true for streaming
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400
        
        messages = data.get('messages', [])
        stream = data.get('stream', False)
        functions = data.get('functions', HA_FUNCTIONS)
        
        # Extract last user message
        user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        if not user_message:
            return jsonify({"error": "No user message found"}), 400
        
        logger.info(f"Conversation request: {user_message[:100]}...")
        
        # Build conversation context
        conversation_context = _build_context(messages)
        
        # Process through our AI (mock for now - will connect to real AI)
        response = _process_conversation(user_message, conversation_context, functions)
        
        if stream:
            return _stream_response(response)
        
        return jsonify(response)
        
    except Exception as e:
        logger.exception("Error in chat completions")
        return jsonify({"error": str(e)}), 500


def _build_context(messages):
    """Build context from message history"""
    context = {
        "system": HA_SYSTEM_PROMPT,
        "history": []
    }
    
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        if role != 'system':
            context["history"].append(f"{role}: {content}")
    
    return context


def _process_conversation(user_message, context, functions):
    """
    Process conversation - this will integrate with our AI system
    For now, returns a basic response
    
    TODO: Connect to actual AI (Ollama, OpenAI, etc.)
    """
    # This is where we'd integrate with our brain/AI system
    # For MVP, return a simple response
    
    response_content = f"I understand you said: '{user_message}'. This is PilotSuite's conversation endpoint. "
    response_content += "Full AI integration coming soon!"
    
    # Check if function calling is needed
    # For now, no function calls
    response = {
        "id": f"chatcmpl-{os.urandom(12).hex()}",
        "object": "chat.completion",
        "created": int(__import__('time').time()),
        "model": "pilotsuite-conversation-1",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content,
                    "function_call": None
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_message),
            "completion_tokens": len(response_content),
            "total_tokens": len(user_message) + len(response_content)
        }
    }
    
    return response


def _stream_response(response):
    """Stream response implementation"""
    # Placeholder for streaming
    import flask
    def generate():
        content = response["choices"][0]["message"]["content"]
        for chunk in content.split():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk + ' '}}]})}\n\n"
        yield "data: [DONE]\n\n"
    
    return flask.Response(generate(), mimetype='text/event-stream')


def register_routes(app):
    """Register conversation routes with Flask app"""
    app.register_blueprint(conversation_bp)
    logger.info("Registered conversation API at /v1/chat/completions")
