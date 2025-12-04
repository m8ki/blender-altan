import json

def reproduce():
    print("Starting reproduction...")
    
    # Mocking the state variables from agent.py
    tool_calls_buffer = []
    
    # Simulating a chunk that might cause the error
    # Case 1: tc_chunk['id'] is None
    chunk_data = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": None, 
                    "function": {}
                }]
            }
        }]
    }
    
    try:
        delta = chunk_data['choices'][0]['delta']
        if 'tool_calls' in delta:
            for tc_chunk in delta['tool_calls']:
                index = tc_chunk['index']
                
                while len(tool_calls_buffer) <= index:
                    tool_calls_buffer.append({"id": "", "function": {"name": "", "arguments": ""}, "type": "function"})
                
                tc = tool_calls_buffer[index]
                
                if 'id' in tc_chunk and tc_chunk['id']:
                    print(f"Processing id: {tc_chunk['id']}")
                    tc['id'] += tc_chunk['id'] # This should crash if id is None
                    
    except TypeError as e:
        print(f"Caught expected TypeError: {e}")
        return

    print("Did not catch TypeError with id=None")

    # Case 2: function arguments is None
    tool_calls_buffer = [{"id": "call_123", "function": {"name": "foo", "arguments": ""}, "type": "function"}]
    chunk_data_args = {
        "choices": [{
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "function": {
                        "arguments": None
                    }
                }]
            }
        }]
    }

    try:
        delta = chunk_data_args['choices'][0]['delta']
        if 'tool_calls' in delta:
            for tc_chunk in delta['tool_calls']:
                index = tc_chunk['index']
                tc = tool_calls_buffer[index]
                
                if 'function' in tc_chunk:
                    fn = tc_chunk['function']
                    if 'arguments' in fn and fn['arguments']:
                        print(f"Processing arguments: {fn['arguments']}")
                        tc['function']['arguments'] += fn['arguments'] # This should crash
                        
    except TypeError as e:
        print(f"Caught expected TypeError: {e}")
        return

    print("Did not catch TypeError with arguments=None")

if __name__ == "__main__":
    reproduce()
