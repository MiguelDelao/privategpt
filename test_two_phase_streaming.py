#!/usr/bin/env python3

import httpx
import asyncio
import json
import sys
from datetime import datetime

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

async def test_two_phase_streaming():
    """Test the complete two-phase streaming flow"""
    
    # 1. Get JWT token from script output
    print(f"{BLUE}1. Getting JWT token...{RESET}")
    import subprocess
    result = subprocess.run(['bash', 'scripts/get-jwt-token.sh'], capture_output=True, text=True)
    
    # Extract token from output
    token = None
    for line in result.stdout.split('\n'):
        if line.startswith('export ACCESS_TOKEN='):
            token = line.split('"')[1]
            break
    
    if not token:
        print(f"{RED}Failed to get JWT token{RESET}")
        return
    
    print(f"{GREEN}✅ Got JWT token{RESET}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 2. Create a conversation
    print(f"\n{BLUE}2. Creating conversation...{RESET}")
    
    async with httpx.AsyncClient() as client:
        # Create conversation
        conversation_data = {
            "title": "Test Two-Phase Streaming"
        }
        
        response = await client.post(
            "http://localhost:8000/api/chat/conversations",
            headers=headers,
            json=conversation_data
        )
        
        if response.status_code != 200:
            print(f"{RED}Failed to create conversation: {response.status_code}{RESET}")
            print(response.text)
            return
        
        conversation = response.json()
        conversation_id = conversation["id"]
        print(f"{GREEN}✅ Created conversation: {conversation_id}{RESET}")
        
        # 3. Prepare stream
        print(f"\n{BLUE}3. Preparing stream...{RESET}")
        
        stream_request = {
            "message": "Hello! Tell me a very short joke.",
            "model": "tinyllama",
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        response = await client.post(
            f"http://localhost:8000/api/chat/conversations/{conversation_id}/prepare-stream",
            headers=headers,
            json=stream_request
        )
        
        if response.status_code != 200:
            print(f"{RED}Failed to prepare stream: {response.status_code}{RESET}")
            print(response.text)
            return
        
        stream_data = response.json()
        stream_url = stream_data["stream_url"]
        stream_token = stream_data["stream_token"]
        print(f"{GREEN}✅ Got stream URL: {stream_url}{RESET}")
        print(f"{YELLOW}   Stream token: {stream_token[:20]}...{RESET}")
        
        # 4. Connect to stream (no auth needed!)
        print(f"\n{BLUE}4. Connecting to stream (no auth headers)...{RESET}")
        
        # Connect to SSE stream
        full_content = ""
        message_id = None
        
        async with client.stream('GET', stream_url) as response:
            if response.status_code != 200:
                print(f"{RED}Failed to connect to stream: {response.status_code}{RESET}")
                return
            
            print(f"{GREEN}✅ Connected to stream!{RESET}")
            print(f"\n{BLUE}Streaming response:{RESET}")
            
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    
                    try:
                        event = json.loads(data)
                        event_type = event.get('type')
                        
                        if event_type == 'stream_start':
                            print(f"{YELLOW}📡 Stream started for conversation: {event['conversation_id']}{RESET}")
                        
                        elif event_type == 'user_message':
                            print(f"{BLUE}👤 User: {event['message']['content']}{RESET}")
                        
                        elif event_type == 'assistant_message_start':
                            message_id = event['message_id']
                            print(f"{YELLOW}🤖 Assistant starting (message_id: {message_id})...{RESET}")
                        
                        elif event_type == 'content_chunk':
                            chunk = event['content']
                            full_content += chunk
                            print(chunk, end='', flush=True)
                        
                        elif event_type == 'assistant_message_complete':
                            print(f"\n{GREEN}✅ Message complete!{RESET}")
                            print(f"{YELLOW}   Message ID: {event['message_id']}{RESET}")
                            print(f"{YELLOW}   Content length: {len(event['content'])} chars{RESET}")
                            if event.get('thinking'):
                                print(f"{YELLOW}   Has thinking content: Yes{RESET}")
                        
                        elif event_type == 'stream_end':
                            print(f"{GREEN}✅ Stream ended successfully!{RESET}")
                        
                        elif event_type == 'error':
                            print(f"{RED}❌ Error: {event['message']}{RESET}")
                    
                    except json.JSONDecodeError:
                        print(f"{RED}Failed to parse event: {data}{RESET}")
        
        print(f"\n{GREEN}✅ Two-phase streaming test completed successfully!{RESET}")
        print(f"\n{BLUE}Summary:{RESET}")
        print(f"- Conversation ID: {conversation_id}")
        print(f"- Message ID: {message_id}")
        print(f"- Stream URL: {stream_url}")
        print(f"- Full response: {full_content}")
        
        # 5. Verify message was saved
        print(f"\n{BLUE}5. Verifying message was saved...{RESET}")
        
        await asyncio.sleep(2)  # Give Celery time to save
        
        response = await client.get(
            f"http://localhost:8000/api/chat/conversations/{conversation_id}/messages",
            headers=headers
        )
        
        if response.status_code == 200:
            messages = response.json()
            print(f"{GREEN}✅ Found {len(messages)} messages in conversation{RESET}")
            for msg in messages:
                print(f"   - {msg['role']}: {msg['content'][:50]}...")
        else:
            print(f"{YELLOW}⚠️  Could not verify messages (status: {response.status_code}){RESET}")

if __name__ == "__main__":
    print(f"{BLUE}🚀 Testing Two-Phase Streaming Architecture{RESET}")
    print(f"{BLUE}{'='*50}{RESET}\n")
    
    asyncio.run(test_two_phase_streaming())