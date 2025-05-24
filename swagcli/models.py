from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class SwaggerParameter(BaseModel):
    name: str
    in_: str = Field(alias="in")
    description: Optional[str] = None
    required: bool = False
    type: Optional[str] = None
    format: Optional[str] = None
    schema_def: Optional[Dict[str, Any]] = Field(default=None, alias="schema")


class SwaggerPath(BaseModel):
    parameters: List[SwaggerParameter] = []
    get: Optional[Dict[str, Any]] = None
    post: Optional[Dict[str, Any]] = None
    put: Optional[Dict[str, Any]] = None
    delete: Optional[Dict[str, Any]] = None


class SwaggerDefinition(BaseModel):
    swagger: str
    info: Dict[str, Any]
    host: Optional[str] = None
    basePath: Optional[str] = None
    schemes: List[str] = []
    paths: Dict[str, SwaggerPath]
    definitions: Optional[Dict[str, Any]] = None


class APIResponse(BaseModel):
    status_code: int
    data: Union[Dict[str, Any], List[Any], str]
    headers: Dict[str, str]
    elapsed: float
