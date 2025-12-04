"""
Agent backend that connects to Blender MCP server and OpenRouter LLM.
"""
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import requests
import json
import os
from typing import List, Dict, Any
import logging
import jwt
import bcrypt
from pymongo import MongoClient
from functools import wraps
import datetime
from bson import ObjectId
from blender_client import BlenderMCPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', 'your-key-here')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'alibaba/tongyi-deepresearch-30b-a3b:free')
ORCHESTRATOR_URL = os.getenv('ORCHESTRATOR_URL', 'http://localhost:5001')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/altan')
JWT_SECRET = os.getenv('JWT_SECRET', 'super-secret-key')

# Database
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client.get_database()
    users_collection = db.users
    chats_collection = db.chats
    logger.info("Connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")

# Auth Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = users_collection.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                 return jsonify({'message': 'Token is invalid!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


# Initialize Blender client
blender_client = BlenderMCPClient(ORCHESTRATOR_URL)

def call_openrouter(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None, stream: bool = False) -> Any:
    """Call OpenRouter API."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "stream": stream
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
            stream=stream
        )
        response.raise_for_status()
        
        if stream:
            return response
        else:
            return response.json()
    except Exception as e:
        logger.error(f"OpenRouter API call failed: {e}")
        raise


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    db_status = "connected"
    try:
        mongo_client.admin.command('ping')
    except:
        db_status = "disconnected"

    return jsonify({
        "status": "healthy",
        "orchestrator_connected": True, # We could check orchestrator health here
        "database": db_status
    })


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    if users_collection.find_one({'username': username}):
        return jsonify({'message': 'Username already exists'}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    user_id = users_collection.insert_one({
        'username': username,
        'password': hashed_password,
        'created_at': datetime.datetime.utcnow()
    }).inserted_id

    return jsonify({'message': 'User created successfully', 'user_id': str(user_id)}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = users_collection.find_one({'username': username})

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, JWT_SECRET, algorithm="HS256")

        return jsonify({'token': token, 'username': username})

    return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/chat/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    """Get conversation history."""
    user_id = str(current_user['_id'])
    chat_doc = chats_collection.find_one({'user_id': user_id})
    
    if not chat_doc:
        return jsonify({"messages": []})
        
    return jsonify({"messages": chat_doc.get('messages', [])})


@app.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    """Handle chat messages."""
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    user_id = str(current_user['_id'])
    
    # Load history from DB
    chat_doc = chats_collection.find_one({'user_id': user_id})
    if not chat_doc:
        history = []
    else:
        history = chat_doc.get('messages', [])

    # Add user message to history
    history.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    
    # System prompt
    system_message = {
        "role": "system",
        "content": """You are a helpful 3D modeling assistant with access to Blender tools. 
You can create 3D objects, set their colors, and render scenes.

When the user asks to create objects:
1. First initialize the scene if not done yet
2. Create the requested objects with appropriate positions
3. Apply colors if requested
4. Render the scene when asked

Be creative with positioning objects so they don't overlap. Use different locations like [0,0,0], [3,0,0], [-3,0,0], etc.

Always explain what you're doing in a friendly way."""
    }
    
    # Filter history for LLM
    llm_history = []
    for m in history:
        msg = {"role": m["role"], "content": m["content"]}
        if "tool_calls" in m:
            msg["tool_calls"] = m["tool_calls"]
        if "tool_call_id" in m:
            msg["tool_call_id"] = m["tool_call_id"]
        llm_history.append(msg)

    messages = [system_message] + llm_history
    
    def generate():
        try:
            # Get tools
            tools = blender_client.get_tools_for_llm()
            
            # Call LLM with streaming
            response = call_openrouter(messages, tools, stream=True)
            
            assistant_content = ""
            tool_calls_buffer = []
            current_tool_call = None
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                line_text = line.decode('utf-8')
                if line_text.startswith("data: "):
                    data_str = line_text[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk['choices'][0]['delta']
                        
                        # Handle content
                        if 'content' in delta and delta['content']:
                            content_chunk = delta['content']
                            assistant_content += content_chunk
                            yield f"data: {json.dumps({'content': content_chunk})}\n\n"
                        
                        # Handle tool calls
                        if 'tool_calls' in delta:
                            for tc_chunk in delta['tool_calls']:
                                index = tc_chunk['index']
                                
                                # Extend buffer if needed
                                while len(tool_calls_buffer) <= index:
                                    tool_calls_buffer.append({"id": "", "function": {"name": "", "arguments": ""}, "type": "function"})
                                
                                tc = tool_calls_buffer[index]
                                
                                if 'id' in tc_chunk and tc_chunk['id']:
                                    tc['id'] += tc_chunk['id']
                                
                                if 'function' in tc_chunk:
                                    fn = tc_chunk['function']
                                    if 'name' in fn and fn['name']:
                                        tc['function']['name'] += fn['name']
                                    if 'arguments' in fn and fn['arguments']:
                                        tc['function']['arguments'] += fn['arguments']

                    except json.JSONDecodeError:
                        continue
            
            # If we have tool calls, execute them
            if tool_calls_buffer:
                # Clean up buffer (remove empty entries if any, though logic above should be safe)
                tool_calls = [tc for tc in tool_calls_buffer if tc['function']['name']]
                
                # Notify frontend about tool execution start
                yield f"data: {json.dumps({'status': 'executing_tools', 'count': len(tool_calls)})}\n\n"
                
                tool_results = []
                for tool_call in tool_calls:
                    function_name = tool_call['function']['name']
                    try:
                        function_args = json.loads(tool_call['function']['arguments'])
                    except:
                        function_args = {}
                    
                    logger.info(f"Executing tool: {function_name} with args: {function_args}")
                    
                    # Call Orchestrator
                    result = blender_client.call_tool(function_name, function_args, user_id=user_id)
                    tool_results.append({
                        "tool": function_name,
                        "result": result
                    })
                    
                    # Stream tool result to frontend
                    yield f"data: {json.dumps({'tool_call': {'tool': function_name, 'result': result}})}\n\n"

                # Append to history
                history.append({
                    "role": "assistant",
                    "content": assistant_content or None,
                    "tool_calls": tool_calls,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
                
                for i, tool_call in enumerate(tool_calls):
                    history.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": json.dumps(tool_results[i]['result']),
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    })
                
                # Call LLM again with tool results
                # Re-construct messages
                llm_history = []
                for m in history:
                    msg = {"role": m["role"], "content": m["content"]}
                    if "tool_calls" in m:
                        msg["tool_calls"] = m["tool_calls"]
                    if "tool_call_id" in m:
                        msg["tool_call_id"] = m["tool_call_id"]
                    llm_history.append(msg)
                
                messages_with_tools = [system_message] + llm_history
                
                logger.info(f"Sending second request to OpenRouter with messages: {json.dumps(messages_with_tools)}")
                
                # Second call to LLM
                response_final = call_openrouter(messages_with_tools, stream=True)
                
                final_content = ""
                for line in response_final.iter_lines():
                    if not line:
                        continue
                    line_text = line.decode('utf-8')
                    if line_text.startswith("data: "):
                        data_str = line_text[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk['choices'][0]['delta']
                            if 'content' in delta and delta['content']:
                                content_chunk = delta['content']
                                final_content += content_chunk
                                yield f"data: {json.dumps({'content': content_chunk})}\n\n"
                        except:
                            pass
                
                # Save final assistant message
                history.append({
                    "role": "assistant",
                    "content": final_content,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
                
            else:
                # No tool calls, just save the assistant content
                history.append({
                    "role": "assistant",
                    "content": assistant_content,
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
            
            # Save to DB
            chats_collection.update_one(
                {'user_id': user_id},
                {'$set': {'messages': history, 'updated_at': datetime.datetime.utcnow()}},
                upsert=True
            )
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/instance', methods=['GET'])
@token_required
def get_instance_info(current_user):
    """Get info about the user's Blender instance."""
    user_id = str(current_user['_id'])
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/instance/{user_id}", timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({"status": "unknown", "error": "Failed to fetch from orchestrator"}), response.status_code
    except Exception as e:
        logger.error(f"Failed to get instance info: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/reset', methods=['POST'])
@token_required
def reset(current_user):
    """Reset conversation history."""
    user_id = str(current_user['_id'])
    chats_collection.delete_one({'user_id': user_id})
    return jsonify({"status": "success", "message": "Conversation reset"})


if __name__ == '__main__':
    logger.info("Starting Agent Backend...")
    logger.info(f"Orchestrator service: {ORCHESTRATOR_URL}")
    logger.info(f"OpenRouter model: {OPENROUTER_MODEL}")
    app.run(host='0.0.0.0', port=5000, debug=False)
