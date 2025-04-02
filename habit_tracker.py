from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import date

# Database setup
DATABASE_URL = "sqlite:///./habit_tracker.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database model
class Habit(Base):
    __tablename__ = "habits"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    frequency = Column(String)
    is_active = Column(Boolean, default=True)

class HabitCompletion(Base):
    __tablename__ = "habit_completions"
    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False)
    completion_date = Column(Date, default=date.today, nullable=False)

# Pydantic schemas
class HabitBase(BaseModel):
    name: str
    description: str
    frequency: str

class HabitCreate(HabitBase):
    pass

class HabitResponse(HabitBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

class HabitCompletionCreate(BaseModel):
    habit_id: int

# FastAPI app
app = FastAPI(title="Habit Tracker")

# Create the database tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Habit Tracker App"}

@app.post("/habits/", response_model=HabitResponse)
def create_habit(habit: HabitCreate, db: Session = Depends(get_db)):
    # Check if habit already exists
    db_habit = db.query(Habit).filter(Habit.name == habit.name).first()
    if db_habit:
        raise HTTPException(status_code=400, detail="Habit already exists")
    
    # Create new habit
    new_habit = Habit(**habit.dict())
    db.add(new_habit)
    db.commit()
    db.refresh(new_habit)
    return new_habit

@app.post("/habits/complete/")
def mark_habit_complete(
    completion: HabitCompletionCreate, db: Session = Depends(get_db)
):
    # Check if the habit exists
    habit = db.query(Habit).filter(Habit.id == completion.habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    # Check if the habit is already marked complete for today
    existing_completion = db.query(HabitCompletion).filter(
        HabitCompletion.habit_id == completion.habit_id,
        HabitCompletion.completion_date == date.today()
    ).first()
    if existing_completion:
        raise HTTPException(
            status_code=400, detail="Habit already marked complete for today"
        )

    # Mark the habit as complete
    new_completion = HabitCompletion(habit_id=completion.habit_id)
    db.add(new_completion)
    db.commit()
    db.refresh(new_completion)
    return {"message": "Habit marked as complete", "completion_id": new_completion.id}