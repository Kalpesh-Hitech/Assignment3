import datetime
from typing import Optional
from datetime import date, datetime
from click import DateTime
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import Column, Integer, Nullable, String, create_engine, Date, DateTime
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    Session
)
import re
import enum

app = FastAPI()

DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    priority=Column(String,nullable=False)
    status=Column(String,nullable=False)
    due_date = Column(Date, nullable=False)
    completed_at = Column(DateTime, nullable=True)



Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "low"
    status: Optional[str] = "pending"
    due_date: date
    completed_at: Optional[datetime] = None

    # @property
    # def 

    @field_validator("title")
    def validate_title(cls,title:str):
        if len(title)<5:
            raise HTTPException(status_code=422,detail="please enter the atleast 5 character title")
        if title.isnumeric():
            raise HTTPException(status_code=422,detail="please enter the atleast character title")
        if not (title.istitle()):
            raise HTTPException(status_code=422,detail="each word have capital letter")
        if bool(re.search(r'[^a-zA-Z0-9 ]', title)):
            raise HTTPException(status_code=422,detail="special character is not allowed!!")
        return title
    
    @field_validator("priority")
    def priority_check(cls,priority):
        if priority not in ["low","medium","high"]:
            raise HTTPException(status_code=422,detail="priority is invalid!!")
        return priority
        
    @field_validator("status")
    def status_check(cls,status):
        if status not in ["pending","in_process","completed"]:
            raise HTTPException(status_code=422,detail="status is invalid!!")
        return status

    @model_validator(mode="after")
    def priority_desc(self):
        if self.priority == "high" and not self.description:
            raise HTTPException(status_code=422,detail="description is needed!!")

        if self.priority == "low" and (self.due_date - date.today()).days > 30:
            raise HTTPException(status_code=422,detail="please give within 30 days !!")

        return self





class TaskResponse(BaseModel):
    id: int
    title: str
    priority: str
    status: str
    due_date: date
    completed_at: Optional[datetime] = None

@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = TaskDB(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

