from typing import Dict, List, Optional, Union, Literal, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    imageUrl: Optional[str] = None

class FileItem(BaseModel):
    code: str

class FileData(BaseModel):
    files: Dict[str, Any] = Field(default_factory=dict)
    dependencies: Dict[str, str] = Field(default_factory=dict)
    title: Optional[str] = None

class GenAICodeRequest(BaseModel):
    workspaceId: Optional[str] = None
    userId: str
    messages: List[Message]
    fileData: Optional[FileData] = None

class ImproveRequest(BaseModel):
    workspaceId: str
    userId: str
    userRequest: str
    fileData: FileData

class WorkspaceUser(BaseModel):
    id: str
    credits: int
    plan: str
