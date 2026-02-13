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

    @property
    def is_overdue(self):
        return (
            self.status != "completed"
            and self.due_date is not None
            and date.today() > self.due_date
        )
    
    @property
    def days_left(self):
        if self.status=="completed":
            return 0
        if not self.due_date:
            return None
        return (
            (self.due_date-date.today()).days
        )
    
    @staticmethod
    def validate_status_transition(old_status, new_status):
        if (old_status=="pending" and new_status=="in_process") or (old_status=="in_process" and new_status=="completed") or (old_status==new_status):
            return True
        return False
    
    @staticmethod
    def can_create_high_priority(db):
        db_high=db.query(TaskDB).filter(TaskDB.priority=="high", TaskDB.status=="pending").count()
        if(db_high>=5):
            raise HTTPException(status_code=422,detail="high pending is more than 5")
        return {"message":"created or updated"}



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
    is_overdue:bool
    days_left:int

@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    if(task.priority=="high" and task.status=="pending"):   
        TaskDB.can_create_high_priority(db)
    db_task = TaskDB(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_by_id(task_id: int, task: TaskCreate, db: Session = Depends(get_db)):
    db_task=db.query(TaskDB).filter(TaskDB.id==task_id).first()
    if not (TaskDB.validate_status_transition(db_task.status,task.status)):
        raise HTTPException(status_code=422,detail="status is wrong!! transsion error!!")
    if(task.priority=="high" and task.status=="pending"):   
        TaskDB.can_create_high_priority(db)
    db_task.title = task.title
    db_task.description = task.description
    db_task.priority = task.priority
    db_task.status = task.status
    db_task.due_date = task.due_date
    db.commit()
    db.refresh(db_task)
    return db_task
