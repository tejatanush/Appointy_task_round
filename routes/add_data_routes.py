from fastapi import APIRouter, Depends, HTTPException,status
from core.add_data import save_user_stuff
from fastapi import Form, File, UploadFile
from typing import Optional,Union
from auth import JWTBearer
data_router=APIRouter()
@data_router.post("/add", dependencies=[Depends(JWTBearer())], summary="Add new user data item")
async def add_user_data(
    token_payload: dict = Depends(JWTBearer()),      
    data_type: str = Form(...),                      
    text: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    image: Optional[Union[UploadFile, str]] = File(None)  
):
    """
    Protected route to add user data (text, image, url).
    Extracts `user_id` from JWT payload automatically.
    """
    if isinstance(image, str) or image is None:
        image = None
    try:
        user_id = token_payload.get("uid")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        if data_type == "text" and text:
            result = await save_user_stuff(user_id, "text", text)

        elif data_type == "url" and url:
            result = await save_user_stuff(user_id, "url", url)

        elif data_type == "image" and image:
            image_bytes = await image.read()
            result = await save_user_stuff(user_id, "image", image_bytes)

        else:
            raise HTTPException(status_code=400, detail="Invalid input for the selected data type.")

        return {
            "message": result["message"],
            "summary": result.get("summary"),
            "tags": result.get("tags"),
            "category": result.get("category"),
            "status": "Successfully added to Synapse Brain"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
