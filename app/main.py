from fastapi import FastAPI
from .routers import users, transactions, test, bets

# models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(users.auth_router) # For /token
app.include_router(users.user_router) # For /users
app.include_router(transactions.router) # For /transactions
app.include_router(test.router) # For /test
app.include_router(bets.router) # For /bets

@app.get("/")
def read_root():
    return {"message": "Welcome to the Cricket Betting App"}
