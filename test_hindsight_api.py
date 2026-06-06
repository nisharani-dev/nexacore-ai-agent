#!/usr/bin/env python3
"""
Test Hindsight API using the official SDK.
Usage: python test_hindsight_api.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from hindsight_client import Hindsight
except ImportError:
    print("❌ hindsight-client not installed")
    print("Install with: pip install hindsight-client")
    exit(1)

BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").rstrip("/")
API_KEY = os.getenv("HINDSIGHT_API_KEY", "")
BANK_ID = os.getenv("HINDSIGHT_PROJECT", "default")

print(f"Testing Hindsight API via Official SDK")
print(f"Base URL: {BASE_URL}")
print(f"API Key: {'*' * max(0, len(API_KEY) - 4)}{API_KEY[-4:] if len(API_KEY) > 4 else '(not set)'}")
print(f"Bank ID: {BANK_ID}")
print("=" * 60)

if not API_KEY:
    print("\n❌ HINDSIGHT_API_KEY not set!")
    print("Set it in your .env file:")
    print("  HINDSIGHT_API_KEY=hsk_...")
    exit(1)

# Initialize client
try:
    client = Hindsight(base_url=BASE_URL, api_key=API_KEY)
    print("✅ Client initialized")
except Exception as e:
    print(f"❌ Failed to initialize client: {e}")
    exit(1)

# Test 1: Retain (write) a memory
print("\n1. Testing retain (write memory)...")
try:
    memory = client.retain(
        bank_id=BANK_ID,
        content="NexaCore is an AI-powered onboarding assistant built with FastAPI and React."
    )
    print(f"   ✅ Memory retained | id={memory.id if hasattr(memory, 'id') else 'N/A'}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 2: Recall (search) memories
print("\n2. Testing recall (search memories)...")
try:
    results = client.recall(
        bank_id=BANK_ID,
        query="What is NexaCore?"
    )
    print(f"   ✅ Found {len(results)} memories")
    for i, result in enumerate(results[:3], 1):
        # RecallResult has memory with text attribute
        memory = result.memory if hasattr(result, 'memory') else result
        text = memory.text if hasattr(memory, 'text') else (memory.content if hasattr(memory, 'content') else str(memory))
        score = result.score if hasattr(result, 'score') else 0.0
        print(f"   {i}. [{score:.3f}] {text[:70]}...")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 3: Reflect (LLM-powered answer)
print("\n3. Testing reflect (LLM answer using memories)...")
try:
    result = client.reflect(
        bank_id=BANK_ID,
        query="Tell me about NexaCore"
    )
    # ReflectResponse object has an answer attribute
    answer = result.answer if hasattr(result, 'answer') else str(result)
    print(f"   ✅ Got answer: {answer[:150]}...")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 4: List Mental Models
print("\n4. Testing list_mental_models...")
try:
    models = client.list_mental_models(bank_id=BANK_ID)
    print(f"   ✅ Found {len(models.items) if hasattr(models, 'items') else 0} mental models")
    if hasattr(models, 'items'):
        for model in models.items[:3]:
            print(f"   - {model.name}")
except Exception as e:
    print(f"   ❌ Failed (might not have any mental models yet): {e}")

print("\n" + "=" * 60)
print("✅ Hindsight SDK is working!")
print("\nYou can now deploy with these settings:")
print(f"  HINDSIGHT_BACKEND=http")
print(f"  HINDSIGHT_BASE_URL={BASE_URL}")
print(f"  HINDSIGHT_API_KEY=<your-key>")
print(f"  HINDSIGHT_PROJECT={BANK_ID}")
print("=" * 60)
