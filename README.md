# Cricket Fantasy Betting App - Backend

This project is the backend for a cricket fantasy betting application. It is built using Python with the FastAPI framework, PostgreSQL for the database, and SQLAlchemy as the ORM. The application provides a RESTful API for user management, authentication, and will be extended to handle betting, transactions, and live sports data integration.

## Technology Stack

*   **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
*   **Database:** [PostgreSQL](https://www.postgresql.org/)
*   **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
*   **Data Validation:** [Pydantic](https://pydantic-docs.helpmanual.io/)
*   **Authentication:** JWT (JSON Web Tokens) with Passlib for password hashing.
*   **Containerization:** [Docker](https://www.docker.com/) for running the PostgreSQL database.

---

## Project Structure

The project is structured as a Python package (`app`) to ensure proper import resolution and maintainability.

```
backend/
├── app/                    # Main application package
│   ├── __init__.py         # Makes 'app' a Python package
│   ├── crud.py             # Contains database operation functions (Create, Read, Update, Delete)
│   ├── database.py         # SQLAlchemy engine, session, and Base configuration
│   ├── main.py             # Main FastAPI application, defines API endpoints
│   ├── models.py           # SQLAlchemy ORM models (defines database tables)
│   ├── schemas.py          # Pydantic models for data validation and serialization
│   ├── security.py         # Handles password hashing, JWT creation, and authentication logic
│   └── scripts/
│       └── initialize_database.py # Script to create and seed the database tables
├── .env                    # Local environment variables (DATABASE_URL) - Not committed
├── .env.example            # Example environment file
├── requirements.txt        # Python dependencies
└── venv/                   # Python virtual environment
```

### File Explanations

*   **`app/main.py`**: This is the entry point of the application. It defines the FastAPI app instance and includes all the API endpoints (e.g., `/users/`, `/token`). It ties together all the other modules to handle incoming requests.

*   **`app/database.py`**: Establishes the connection to the PostgreSQL database. It creates the SQLAlchemy `engine` and the `SessionLocal` class, which is used to create new database sessions for each request.

*   **`app/models.py`**: Defines the structure of our database tables using Python classes. Each class maps to a table and its attributes map to columns. SQLAlchemy uses these models to interact with the database in an object-oriented way.

*   **`app/schemas.py`**: Contains Pydantic models. These are used to define the expected shape of data for API requests (e.g., `UserCreate`) and responses (e.g., `User`). They provide powerful data validation and serialization (converting data to and from JSON).

*   **`app/crud.py`**: Stands for **C**reate, **R**ead, **U**pdate, **D**elete. This file separates the database interaction logic from the endpoint logic. Functions here take a database session and data, and perform the necessary database queries.

*   **`app/security.py`**: Centralizes all security-related logic. It contains functions for hashing and verifying passwords (using `passlib`) and for creating and managing JWTs for authentication.

*   **`app/scripts/initialize_database.py`**: A utility script to set up the database from scratch. It creates all tables defined in `models.py` and seeds the `roles` table with initial data ('admin', 'master', etc.).

---

## Getting Started

Follow these steps to get the application running locally.

### Prerequisites

*   Python 3.10+
*   Docker and Docker Compose

### 1. Database Setup (Docker)

We use Docker to run a PostgreSQL database, which avoids having to install it on your system directly.

1.  **Start the PostgreSQL container:**
    ```bash
    # Replace 'YourSecretPassword' with a real password
    docker run --name bettingDatabase -e POSTGRES_PASSWORD=YourSecretPassword -e POSTGRES_DB=betting -p 5432:5432 -d postgres:alpine
    ```

### 2. Application Setup

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    ```

2.  **Install dependencies:**
    ```bash
    venv/bin/pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    *   Copy the example `.env` file: `cp .env.example .env`
    *   Edit the `.env` file and set the `DATABASE_URL` with the password you used in the `docker run` command. Remember to URL-encode any special characters in your password (e.g., `@` becomes `%40`).
    ```env
    DATABASE_URL="postgresql://postgres:YourSecretPassword@localhost:5432/betting"
    ```

4.  **Initialize the Database:**
    Run the initialization script as a module to create the tables and seed the roles.
    ```bash
    venv/bin/python -m app.scripts.initialize_database
    ```

### 3. Running the Application

With the database running and the environment set up, start the FastAPI server:

```bash
venv/bin/uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

---

## API Endpoints

The application provides interactive API documentation via Swagger UI and ReDoc.

*   **Swagger UI:** `http://127.0.0.1:8000/docs`
*   **ReDoc:** `http://127.0.0.1:8000/redoc`

### Current Endpoints

*   **`POST /users/`**: Creates a new user.
    *   **Request Body:**
        ```json
        {
          "username": "string",
          "password": "string",
          "role": "player",
          "parent_username": "some_dealer_username"
        }
        ```

*   **`POST /token`**: Authenticates a user and returns a JWT access token.
    *   **Request Body:** `x-www-form-urlencoded` with `username` and `password` fields.
