from fastapi import Depends, FastAPI, HTTPException
from main import TaskDB
def get_task_or_404(db, id):
    db_task = db.query(TaskDB).filter(TaskDB.id == id).first()
    if db_task is None:
        raise HTTPException(status_code=422, detail="please enter valid id!!")
    return db_task

def apply_filter(db,queryparm,filters):
    if(queryparm=="status"):
        db_task=db.query(TaskDB).filter(TaskDB.status==filters)
        if db_task is not None:
            raise HTTPException(status_code=422,detail="there is not values in status!!")
        return db_task
    if(queryparm=="priority"):
        db_task=db.query(TaskDB).filter(TaskDB.priority==filters)
        if db_task is not None:
            raise HTTPException(status_code=422,detail="there is not values in priority!!")
        return db_task
    return None
    