from fastapi import FastAPI
from .routers import users

# models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(users.auth_router) # For /token
app.include_router(users.user_router) # For /users

@app.get("/")
def read_root():
    return {"message": "Welcome to the Cricket Betting App"}
