"""
FastAPI Integration for ProactiveAgent
Production-ready web API for Vibecoderz integration

Run with: uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
"""
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from proactive_agent import ProactiveAgent, StudentEvent

# Load environment variables
load_dotenv()

# FastAPI app initialization
app = FastAPI(
    title="ProactiveAgent API",
    description="Vibecoderz Proactive Learning Intervention System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent_instance: Optional[ProactiveAgent] = None

# Pydantic models for API
class StudentEventRequest(BaseModel):
    """Request model for student events"""
    user_id: str = Field(..., description="Unique student identifier")
    event_type: str = Field(..., description="Type of event: quiz_failure, help_request, session_timeout")
    topic: str = Field(..., description="Educational topic related to the event")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "student_123",
                "event_type": "quiz_failure",
                "topic": "CSS Flexbox",
                "metadata": {
                    "quiz_score": 0.4,
                    "attempts": 2,
                    "time_spent": 45
                }
            }
        }

class InterventionResponse(BaseModel):
    """Response model for interventions"""
    action: str = Field(..., description="Action taken by the agent")
    user_message: Optional[str] = Field(None, description="Message to display to the user")
    artifact: Optional[Dict[str, Any]] = Field(None, description="Generated learning artifact")
    user_id: str = Field(..., description="Student identifier")
    timestamp: str = Field(..., description="Intervention timestamp")
    intervention_id: Optional[str] = Field(None, description="Unique intervention identifier")

class UserProfileResponse(BaseModel):
    """Response model for user learning profiles"""
    user_id: str
    total_events: int
    intervention_count: int
    struggle_topics: List[str]
    last_intervention: Optional[str]
    learning_patterns: Dict[str, Any]

class SystemStatusResponse(BaseModel):
    """Response model for system status"""
    status: str
    total_users: int
    total_events: int
    total_interventions: int
    uptime: str
    api_version: str

# Dependency to get agent instance
async def get_agent() -> ProactiveAgent:
    """Dependency to get the agent instance"""
    global agent_instance
    if agent_instance is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="GEMINI_API_KEY not configured. Please check environment variables."
            )
        agent_instance = ProactiveAgent(api_key)
    return agent_instance

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    try:
        await get_agent()
        print("🤖 ProactiveAgent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ProactiveAgent: {e}")

# API Routes

@app.get("/", summary="Health Check")
async def root():
    """Health check endpoint"""
    return {"message": "ProactiveAgent API is running", "status": "healthy"}

@app.get("/status", response_model=SystemStatusResponse, summary="System Status")
async def get_system_status(agent: ProactiveAgent = Depends(get_agent)):
    """Get overall system status and metrics"""
    total_users = len(agent.user_memory)
    total_events = sum(len(memory.get('struggle_history', [])) for memory in agent.user_memory.values())
    total_interventions = sum(memory.get('intervention_count', 0) for memory in agent.user_memory.values())
    
    return SystemStatusResponse(
        status="operational",
        total_users=total_users,
        total_events=total_events,
        total_interventions=total_interventions,
        uptime="N/A",  # Would implement with actual uptime tracking
        api_version="1.0.0"
    )

@app.post("/events", response_model=InterventionResponse, summary="Process Student Event")
async def process_student_event(
    event_request: StudentEventRequest,
    background_tasks: BackgroundTasks,
    agent: ProactiveAgent = Depends(get_agent)
):
    """
    Process a student learning event and potentially create an intervention.
    
    This endpoint is the main integration point for Vibecoderz platform.
    Send student events here to trigger proactive learning assistance.
    """
    try:
        # Convert request to StudentEvent
        event = StudentEvent(
            user_id=event_request.user_id,
            event_type=event_request.event_type,
            topic=event_request.topic,
            metadata=event_request.metadata,
            timestamp=datetime.now()
        )
        
        # Process the event
        result = await agent.process_student_event(event)
        
        # Parse artifact if intervention was created
        artifact = None
        if result.get('action') == 'intervention_created':
            try:
                response_text = str(result.get('response', ''))
                if '{' in response_text and '}' in response_text:
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    json_str = response_text[start:end]
                    artifact = json.loads(json_str)
            except Exception as e:
                print(f"Warning: Could not parse artifact JSON: {e}")
        
        # Add analytics tracking in background
        background_tasks.add_task(
            track_intervention_analytics, 
            event_request.user_id, 
            event_request.event_type, 
            result.get('action')
        )
        
        return InterventionResponse(
            action=result.get('action', 'unknown'),
            user_message=result.get('user_message'),
            artifact=artifact,
            user_id=event_request.user_id,
            timestamp=result.get('timestamp', datetime.now().isoformat()),
            intervention_id=f"int_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{event_request.user_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process event: {str(e)}")

@app.get("/users/{user_id}/profile", response_model=UserProfileResponse, summary="Get User Learning Profile")
async def get_user_profile(user_id: str, agent: ProactiveAgent = Depends(get_agent)):
    """Get detailed learning profile for a specific user"""
    user_memory = agent.user_memory.get(user_id)
    
    if not user_memory:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    struggle_history = user_memory.get('struggle_history', [])
    topics = [event['topic'] for event in struggle_history]
    unique_topics = list(set(topics))
    
    # Analyze learning patterns
    event_types = [event.get('event_type', 'unknown') for event in struggle_history]
    patterns = {
        "most_common_struggle_type": max(set(event_types), key=event_types.count) if event_types else None,
        "topics_needing_attention": unique_topics[:3],  # Top 3 struggle topics
        "recent_activity": len([e for e in struggle_history if 
                               datetime.fromisoformat(e.get('timestamp', '2024-01-01T00:00:00')) > 
                               datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)]),
    }
    
    return UserProfileResponse(
        user_id=user_id,
        total_events=len(struggle_history),
        intervention_count=user_memory.get('intervention_count', 0),
        struggle_topics=unique_topics,
        last_intervention=user_memory.get('last_intervention'),
        learning_patterns=patterns
    )

@app.get("/users", summary="List All Users")
async def list_users(agent: ProactiveAgent = Depends(get_agent)):
    """Get list of all users with basic stats"""
    users = []
    for user_id, memory in agent.user_memory.items():
        users.append({
            "user_id": user_id,
            "event_count": len(memory.get('struggle_history', [])),
            "intervention_count": memory.get('intervention_count', 0),
            "last_activity": memory.get('struggle_history', [{}])[-1].get('timestamp') if memory.get('struggle_history') else None
        })
    
    return {"users": users, "total_count": len(users)}

@app.post("/users/{user_id}/reset", summary="Reset User Profile")
async def reset_user_profile(user_id: str, agent: ProactiveAgent = Depends(get_agent)):
    """Reset a user's learning profile (for testing/demo purposes)"""
    if user_id in agent.user_memory:
        del agent.user_memory[user_id]
        return {"message": f"User {user_id} profile reset successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

@app.post("/generate-artifact", summary="Generate Learning Artifact")
async def generate_learning_artifact(
    topic: str,
    agent: ProactiveAgent = Depends(get_agent)
):
    """Directly generate a learning artifact for a given topic (testing endpoint)"""
    try:
        tool = agent._create_generate_tool()
        result = tool.func(topic)
        artifact = json.loads(result)
        
        return {
            "topic": topic,
            "artifact": artifact,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate artifact: {str(e)}")

# Webhook endpoints for Vibecoderz platform integration
@app.post("/webhooks/quiz-completed", summary="Quiz Completion Webhook")
async def quiz_completed_webhook(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    agent: ProactiveAgent = Depends(get_agent)
):
    """Webhook endpoint for quiz completion events from Vibecoderz platform"""
    required_fields = ['user_id', 'quiz_topic', 'score']
    if not all(field in data for field in required_fields):
        raise HTTPException(status_code=400, detail=f"Missing required fields: {required_fields}")
    
    # Determine if this is a failure event
    score = float(data['score'])
    if score < 0.6:  # 60% threshold
        event_request = StudentEventRequest(
            user_id=data['user_id'],
            event_type="quiz_failure",
            topic=data['quiz_topic'],
            metadata={
                "quiz_score": score,
                "attempts": data.get('attempts', 1),
                "time_spent": data.get('time_spent', 0)
            }
        )
        
        # Process in background
        background_tasks.add_task(
            process_student_event_background,
            event_request,
            agent
        )
    
    return {"status": "received", "will_process": score < 0.6}

@app.post("/webhooks/help-request", summary="Help Request Webhook")
async def help_request_webhook(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    agent: ProactiveAgent = Depends(get_agent)
):
    """Webhook endpoint for help request events from Vibecoderz platform"""
    event_request = StudentEventRequest(
        user_id=data['user_id'],
        event_type="help_request",
        topic=data['topic'],
        metadata=data.get('metadata', {})
    )
    
    background_tasks.add_task(
        process_student_event_background,
        event_request,
        agent
    )
    
    return {"status": "received"}

# Background task functions
async def process_student_event_background(event_request: StudentEventRequest, agent: ProactiveAgent):
    """Process student event in background"""
    try:
        event = StudentEvent(
            user_id=event_request.user_id,
            event_type=event_request.event_type,
            topic=event_request.topic,
            metadata=event_request.metadata,
            timestamp=datetime.now()
        )
        await agent.process_student_event(event)
    except Exception as e:
        print(f"Background processing error: {e}")

async def track_intervention_analytics(user_id: str, event_type: str, action: str):
    """Track analytics for interventions (placeholder for real analytics)"""
    # In production, this would send to analytics platform
    analytics_data = {
        "user_id": user_id,
        "event_type": event_type,
        "action": action,
        "timestamp": datetime.now().isoformat()
    }
    print(f"📊 Analytics: {analytics_data}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)