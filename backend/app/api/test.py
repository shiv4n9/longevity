from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/test", tags=["test"])

@router.post("/collect-sync")
async def test_collection_sync(db: AsyncSession = Depends(get_db)):
    """Test endpoint to run collection synchronously for debugging"""
    collection_service = CollectionService()
    
    messages = []
    
    async def progress_callback(message: str):
        messages.append(message)
        print(f"[TEST PROGRESS] {message}")
    
    try:
        result = await collection_service.collect_all_metrics(db, "vsrx", progress_callback)
        return {
            "status": "success",
            "result": result,
            "progress_messages": messages
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "progress_messages": messages
        }
