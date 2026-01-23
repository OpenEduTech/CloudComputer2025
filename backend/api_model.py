from pydantic import BaseModel

class ConceptModel(BaseModel):
    concept:str
    
class DifinitionModel(BaseModel):
    concept:str
    domain:str
    
class QaModel(BaseModel):
    concept:str
    question:str