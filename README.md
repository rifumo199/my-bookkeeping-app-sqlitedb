# Python Bookkeeping App

A simple desktop application for managing customer information, built with Python, Tkinter, and SQLite.

## Features

*   **Full CRUD Functionality**: Create, Read, Update, and Delete customer records.
*   **Live Search**: Dynamically filter the customer list by name as you type.
*   **Modern UI**: A clean, modern dark theme is applied using the `sv-ttk` library.
*   **Persistent Storage**: All data is saved locally in an SQLite database (`mybookkeeping.db`).
*   **Robust and User-Friendly**: Includes confirmation dialogs for deletions and graceful error handling.

## How to Run

1.  **Prerequisites**:
    *   Python 3
    *   `tkinter` library (On Debian/Ubuntu, install with `sudo apt-get install python3-tk`)

2.  **Clone the repository**:
    ```bash
    git clone https://github.com/rifumo199/my-bookkeeping-app-sqlitedb.git
    cd my-bookkeeping-app-sqlitedb
    ```

3.  **Install dependencies and run**:
    ```bash
    pip install sv-ttk
    python3 bookkeeping.py
    ```