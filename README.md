- [Chess Dashboard](#chess-dashboard)
  - [Project Structure](#project-structure)
  - [Setup and Installation](#setup-and-installation)
    - [Local Development](#local-development)
    - [Docker Installation](#docker-installation)
  - [Configuration](#configuration)
  - [Usage](#usage)

# Chess Dashboard

A comprehensive, full-stack application designed to analyze chess games from chess.com with the TWIC Database (This Week In Chess).
It provides deep insights into player performance, opening repertoires, clock management, playstyle inference, and peer comparisons, utilizing a FastAPI backend and a Streamlit frontend.

## Project Structure

The codebase is organized into modular components separating data ingestion, feature engineering, API routing, and frontend presentation.

* **aggregations/**: Contains logic for computing statistical aggregates, such as peer comparisons, recent opening repertoires, and overall metric tables.
* **api/**: The FastAPI backend application. Includes `main.py` for application initialization and various routing modules (`route_analyze.py`, `route_deep_dive.py`, etc.) defining the REST API endpoints.
* **app/**: The Streamlit frontend application. Contains the main entry point (`streamlit_app.py`), sidebars, API client logic, and a `components/` subdirectory holding individual UI widgets (e.g., KPIs, rating progression, peer reports, volume outcomes).
* **chesscom/**: Core data ingestion modules for interacting with the Chess.com API. Handles fetching user archives, caching configurations, parsing PGNs, and inserting cleaned data into local DuckDB databases.
* **features/**: Feature engineering pipelines. Responsible for extracting actionable data points from raw games, such as time management metrics, opening classifications, result mapping, and player perspective normalization.
* **ml/**: Analytical and machine learning modules. Contains logic for playstyle inference, engine evaluation diagnostics, player profiling, and building polyglot opening books.
* **notebooks/**: Jupyter notebooks (`chessCom.ipynb`, `twic.ipynb`) used for initial data exploration, prototyping, and ad-hoc analysis.
* **scripts/**: Utility and testing scripts used for validating pipelines (e.g., testing peer reports, style inference, and data integration) independently of the main application.
* **storage/**: Database and caching logic to manage application state and intermediate analytical data efficiently.
* **twic/**: Modules dedicated to downloading and processing "The Week in Chess" (TWIC) data, building reference databases, and extracting Grandmaster benchmark models (K-Means, PCA).

## Setup and Installation

### Local Development

1. **Clone the repository:**
```bash
git clone <repository_url>
cd chessdashboard

```

2. **Create and activate a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate 

```

3. **Install the required dependencies:**
```bash
pip install -r requirements.txt

```

4. **Environment Configuration:**
Copy the example environment file and configure the necessary variables.
```bash
cp .env.example .env

```

5. **Run the Backend (FastAPI):**
Start the API server in a terminal window. The API must be running for the frontend to retrieve data.
```bash
uvicorn api.main:app --reload --port 8000

```

6. **Run the Frontend (Streamlit):**
In a separate terminal window, ensure your virtual environment is active and run:
```bash
streamlit run app/streamlit_app.py

```

### Docker Installation

If you prefer to run the application using Docker, the provided `dockerfile` and `docker-compose.yml` make it straightforward to deploy the stack.

1. Ensure Docker and Docker Compose are installed on your machine.
2. Configure your `.env` file by copying `.env.example` to `.env`.
3. Build and start the containers:
    ```bash
    docker-compose up --build

    ```

## Configuration

The application behavior can be modified using the `.env` file. Refer to `.env.example` for the required keys. Common configurations include API base URLs (pointing to the FastAPI backend), database file paths, and environment toggles. Ensure these match your chosen deployment method (Local vs. Docker).

## Usage

Once both the FastAPI backend and Streamlit frontend are running:

1. Navigate to the Streamlit UI in your web browser (typically accessible at `http://localhost:8501`).
2. Enter a valid Chess.com username in the provided sidebar input field.
3. The backend will fetch the user's game archives, process the data through the analytical pipelines, and cache the results.
4. The frontend will populate the dashboard, allowing you to navigate through various tabs to view overview metrics, clock management statistics, opening repertoires, playstyle diagnostics, and detailed peer group comparisons.