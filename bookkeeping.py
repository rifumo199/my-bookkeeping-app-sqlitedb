import sqlite3
import tkinter as tk
from tkinter import messagebox

from tkinter import ttk

class BookkeepingApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Bookkeeping App")

        try:
            # Connect to SQLite DB and get cursor
            self.conn = sqlite3.connect("mybookkeeping.db")
            self.cursor = self.conn.cursor()
            print("Database connection to 'mybookkeeping.db' successful!")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to connect to database: {e}")
            self.root.destroy()
            return

        self.create_table()
        # Create UI widgets
        self.create_widgets()

        # Load initial data into the view
        self.load_customers()

        # Ensure DB connection is closed when window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_table(self):
        """Create the customers table if it doesn't already exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                contact TEXT
            )
        ''')
        self.conn.commit()

    def create_widgets(self):
        """Create and layout the UI elements."""
        # --- Main container frame ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(main_frame, text="Add New Customer", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # --- Input Fields and Labels ---
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(input_frame, width=40)
        self.name_entry.grid(row=0, column=1, pady=2)

        ttk.Label(input_frame, text="Email:").grid(row=1, column=0, sticky="w", pady=2)
        self.email_entry = ttk.Entry(input_frame, width=40)
        self.email_entry.grid(row=1, column=1, pady=2)

        ttk.Label(input_frame, text="Contact:").grid(row=2, column=0, sticky="w", pady=2)
        self.contact_entry = ttk.Entry(input_frame, width=40)
        self.contact_entry.grid(row=2, column=1, pady=2)

        # --- Action Button ---
        ttk.Button(input_frame, text="Add Customer", command=self.add_customer).grid(row=3, column=0, columnspan=2, pady=10)

        # --- Customer List Frame (using Treeview) ---
        tree_frame = ttk.LabelFrame(main_frame, text="Customers", padding="10")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('id', 'name', 'email', 'contact')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')

        # Define headings and column properties
        self.tree.heading('id', text='ID')
        self.tree.column('id', width=40, anchor=tk.CENTER)
        self.tree.heading('name', text='Name')
        self.tree.column('name', width=150)
        self.tree.heading('email', text='Email')
        self.tree.column('email', width=200)
        self.tree.heading('contact', text='Contact')
        self.tree.column('contact', width=120)

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Delete Button ---
        delete_button = ttk.Button(main_frame, text="Delete Selected Customer", command=self.delete_customer)
        delete_button.pack(pady=5)

    def load_customers(self):
        """Clear the treeview and load all customers from the database."""
        self.root.config(cursor="watch") # Set a busy cursor
        self.root.update_idletasks() # Ensure cursor updates immediately
        try:
            # Clear existing items to prevent duplication
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Fetch and display new data
            self.cursor.execute("SELECT id, name, email, contact FROM customers ORDER BY id")
            customers = self.cursor.fetchall()
            for customer in customers:
                self.tree.insert('', tk.END, values=customer)
        finally:
            self.root.config(cursor="") # Reset to the default cursor

    def add_customer(self):
        """Handle adding a new customer to the database."""
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        contact = self.contact_entry.get().strip()

        if not name:
            messagebox.showerror("Error", "Name is a required field!")
            return

        self.cursor.execute("INSERT INTO customers (name, email, contact) VALUES (?, ?, ?)",
                            (name, email, contact))
        self.conn.commit()
        messagebox.showinfo("Success", "Customer added successfully!")
        self.name_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.contact_entry.delete(0, tk.END)

        # Refresh the customer list to show the new entry
        self.load_customers()

    def delete_customer(self):
        """Delete the selected customer from the database."""
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a customer to delete.")
            return

        # Get the data of the selected row
        customer_data = self.tree.item(selected_item, 'values')
        customer_id = customer_data[0]
        customer_name = customer_data[1]

        # Ask for confirmation
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {customer_name}?"):
            try:
                self.cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
                self.conn.commit()
                messagebox.showinfo("Success", "Customer deleted successfully.")
                self.load_customers() # Refresh the list
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to delete customer: {e}")

    def on_closing(self):
        """Handles the window closing event to safely close the DB connection."""
        self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BookkeepingApp(root)
    root.mainloop()
