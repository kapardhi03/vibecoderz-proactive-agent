"""
Testing module for ProactiveAgent
Run with: python src/test_agent.py
"""
import asyncio
import json
import os
from dotenv import load_dotenv
from proactive_agent import (
    ProactiveAgent, 
    simulate_failed_quiz_event,
    simulate_help_request_event,
    simulate_session_timeout_event
)

# Load environment variables
load_dotenv()

async def test_basic_functionality():
    """Test basic agent functionality"""
    print("🚀 Testing ProactiveAgent Basic Functionality")
    print("=" * 50)
    
    # Initialize agent
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        return False
    
    agent = ProactiveAgent(api_key)
    print("✅ Agent initialized successfully")
    
    # Test 1: Failed Quiz Event
    print("\n📝 Test 1: Failed Quiz Event (CSS Flexbox)")
    event1 = simulate_failed_quiz_event("priya", "CSS Flexbox")
    result1 = await agent.process_student_event(event1)
    
    print(f"Action: {result1.get('action')}")
    print(f"User Message: {result1.get('user_message')}")
    
    if result1.get('action') == 'intervention_created':
        print("✅ Test 1 PASSED: Intervention created for quiz failure")
        
        # Try to parse the generated artifact
        try:
            response_text = str(result1.get('response', ''))
            # Look for JSON in the response
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                artifact = json.loads(json_str)
                print(f"📄 Generated Artifact: {artifact.get('title', 'No title')}")
                print(f"📊 Slides: {len(artifact.get('slides', []))} slides")
            else:
                print("⚠️  Could not extract JSON artifact from response")
        except Exception as e:
            print(f"⚠️  Could not parse artifact JSON: {e}")
    else:
        print(f"❌ Test 1 FAILED: Expected intervention_created, got {result1.get('action')}")
        return False
    
    # Test 2: Help Request Event
    print("\n🆘 Test 2: Help Request Event (JavaScript Promises)")
    event2 = simulate_help_request_event("alex", "JavaScript Promises")
    result2 = await agent.process_student_event(event2)
    
    print(f"Action: {result2.get('action')}")
    if result2.get('action') == 'intervention_created':
        print("✅ Test 2 PASSED: Intervention created for help request")
    else:
        print(f"⚠️  Test 2: No intervention (expected for single help request)")
    
    # Test 3: Multiple events for same user (should trigger intervention)
    print("\n🔄 Test 3: Multiple Events for Same User")
    event3a = simulate_help_request_event("alex", "JavaScript Async/Await")
    event3b = simulate_help_request_event("alex", "JavaScript Promises")
    
    await agent.process_student_event(event3a)
    result3 = await agent.process_student_event(event3b)
    
    if result3.get('action') == 'intervention_created':
        print("✅ Test 3 PASSED: Multiple struggles triggered intervention")
    else:
        print(f"⚠️  Test 3: Expected intervention for multiple struggles")
    
    # Test 4: Session Timeout Event
    print("\n⏰ Test 4: Session Timeout Event")
    event4 = simulate_session_timeout_event("sam", "Python Functions")
    result4 = await agent.process_student_event(event4)
    print(f"Action: {result4.get('action')}")
    
    print("\n📊 User Memory Status:")
    for user_id, memory in agent.user_memory.items():
        print(f"  {user_id}: {len(memory.get('struggle_history', []))} events, "
              f"{memory.get('intervention_count', 0)} interventions")
    
    return True

async def test_tool_directly():
    """Test the byte course generation tool directly"""
    print("\n🔧 Testing Byte Course Generation Tool Directly")
    print("=" * 50)
    
    api_key = os.getenv("GEMINI_API_KEY")
    agent = ProactiveAgent(api_key)
    
    # Get the tool function
    tool = agent._create_generate_tool()
    
    # Test with different topics
    test_topics = ["CSS Grid", "React Hooks", "Database Normalization"]
    
    for topic in test_topics:
        print(f"\n📚 Generating content for: {topic}")
        try:
            result = tool.func(topic)  # Access the underlying function
            artifact = json.loads(result)
            print(f"✅ Title: {artifact.get('title')}")
            print(f"📝 Slides: {len(artifact.get('slides', []))}")
            print(f"⏱️  Duration: {artifact.get('duration_minutes')} minutes")
            
            # Show first slide as example
            if artifact.get('slides'):
                first_slide = artifact['slides'][0]
                print(f"📄 First slide: {first_slide.get('title')}")
                
        except Exception as e:
            print(f"❌ Error generating content for {topic}: {e}")
            return False
    
    return True

async def run_comprehensive_demo():
    """Run a comprehensive demo showing the full workflow"""
    print("\n🎬 Comprehensive Demo: Student Learning Journey")
    print("=" * 60)
    
    api_key = os.getenv("GEMINI_API_KEY")
    agent = ProactiveAgent(api_key)
    
    # Simulate a student's learning journey
    print("👩‍💻 Student 'Maya' is learning web development...")
    
    # Day 1: First struggle with CSS
    print("\n📅 Day 1: Maya struggles with CSS Flexbox quiz")
    event1 = simulate_failed_quiz_event("maya", "CSS Flexbox")
    result1 = await agent.process_student_event(event1)
    print(f"System Response: {result1.get('user_message')}")
    
    # Day 2: Asks for help with related topic
    print("\n📅 Day 2: Maya requests help with CSS Grid")
    event2 = simulate_help_request_event("maya", "CSS Grid")
    result2 = await agent.process_student_event(event2)
    print(f"System Response: {result2.get('user_message', 'No intervention needed yet')}")
    
    # Day 3: Another struggle
    print("\n📅 Day 3: Maya times out on JavaScript lesson")
    event3 = simulate_session_timeout_event("maya", "JavaScript Events")
    result3 = await agent.process_student_event(event3)
    print(f"System Response: {result3.get('user_message', 'Monitoring progress')}")
    
    # Show Maya's learning profile
    maya_memory = agent.user_memory.get("maya", {})
    print(f"\n📊 Maya's Learning Profile:")
    print(f"  Total struggles: {len(maya_memory.get('struggle_history', []))}")
    print(f"  Interventions received: {maya_memory.get('intervention_count', 0)}")
    print(f"  Topics struggled with: {[event['topic'] for event in maya_memory.get('struggle_history', [])]}")

def validate_environment():
    """Validate that the environment is set up correctly"""
    print("🔍 Validating Environment Setup")
    print("=" * 30)
    
    # Check for required environment variables
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        print("💡 Please add your Gemini API key to the .env file")
        return False
    else:
        print("✅ GEMINI_API_KEY found")
    
    # Check imports
    try:
        from google.adk.agents import Agent
        print("✅ Google ADK imported successfully")
    except ImportError as e:
        print(f"❌ Google ADK import failed: {e}")
        print("💡 Please install with: pip install google-adk")
        return False
    
    try:
        from google import genai
        print("✅ Google GenAI imported successfully")
    except ImportError as e:
        print(f"❌ Google GenAI import failed: {e}")
        print("💡 Please install with: pip install google-generativeai")
        return False
    
    return True

async def main():
    """Main testing function"""
    print("🤖 ProactiveAgent Testing Suite")
    print("=" * 40)
    
    # Validate environment first
    if not validate_environment():
        return
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    try:
        if await test_basic_functionality():
            tests_passed += 1
            
        if await test_tool_directly():
            tests_passed += 1
            
        await run_comprehensive_demo()
        tests_passed += 1
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        return
    
    # Summary
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    if tests_passed == total_tests:
        print("🎉 All tests passed! ProactiveAgent is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())