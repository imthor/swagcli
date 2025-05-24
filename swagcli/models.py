from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl


class SwaggerParameter(BaseModel):
    name: str
    in_: str = Field(alias="in")
    description: Optional[str] = None
    required: bool = False
    type: Optional[str] = None
    format: Optional[str] = None
    schema_def: Optional[Dict] = Field(default=None, alias="schema")


class SwaggerPath(BaseModel):
    parameters: List[SwaggerParameter] = []
    get: Optional[Dict] = None
    post: Optional[Dict] = None
    put: Optional[Dict] = None
    delete: Optional[Dict] = None


class SwaggerDefinition(BaseModel):
    swagger: str
    info: Dict
    host: Optional[str] = None
    basePath: Optional[str] = None
    schemes: List[str] = []
    paths: Dict[str, SwaggerPath]
    definitions: Optional[Dict] = None


class APIResponse(BaseModel):
    status_code: int
    data: Union[Dict, List, str]
    headers: Dict[str, str]
    elapsed: float
