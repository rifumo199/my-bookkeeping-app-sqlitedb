import sqlite3
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

from tkinter import ttk
import sv_ttk

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

        self._create_input_frame(main_frame)
        self._create_search_frame(main_frame)
        self._create_treeview_frame(main_frame)
        self._create_action_buttons(main_frame)
        self._create_status_bar(main_frame)

    def _create_input_frame(self, parent_frame):
        # --- Input Frame ---
        input_frame = ttk.LabelFrame(parent_frame, text="Add New Customer", padding="10")
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

    def _create_search_frame(self, parent_frame):
        # --- Search Frame ---
        search_frame = ttk.LabelFrame(parent_frame, text="Search Customers", padding="10")
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Search by Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self.search_customers)
    
    def _create_treeview_frame(self, parent_frame):
        # --- Customer List Frame (using Treeview) ---
        tree_frame = ttk.LabelFrame(parent_frame, text="Customers", padding="10")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('id', 'name', 'email', 'contact')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')

        # Define headings and column properties
        self.tree.heading('id', text='ID', command=lambda: self.sort_by_column('id', False))
        self.tree.column('id', width=40, anchor=tk.CENTER)
        self.tree.heading('name', text='Name', command=lambda: self.sort_by_column('name', False))
        self.tree.column('name', width=150)
        self.tree.heading('email', text='Email', command=lambda: self.sort_by_column('email', False))
        self.tree.column('email', width=200)
        self.tree.heading('contact', text='Contact', command=lambda: self.sort_by_column('contact', False))
        self.tree.column('contact', width=120)

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click event to the treeview for editing
        self.tree.bind("<Double-1>", self.open_edit_window)

        # Keep track of the last sorted column
        self._last_sort_column = None
        self._last_sort_reverse = False

    def _create_action_buttons(self, parent_frame):
        # --- Delete Button ---
        delete_button = ttk.Button(parent_frame, text="Delete Selected Customer", command=self.delete_customer)
        delete_button.pack(pady=5)

    def _create_status_bar(self, parent_frame):
        # --- Status Bar ---
        self.status_bar = ttk.Label(parent_frame, text="Ready", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_timer = None

    def load_customers(self, search_term=""):
        """Clear the treeview and load all customers from the database."""
        self.root.config(cursor="watch") # Set a busy cursor
        self.root.update_idletasks() # Ensure cursor updates immediately
        try:
            # Clear existing items to prevent duplication
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Fetch and display new data, with optional search
            if search_term:
                query = "SELECT id, name, email, contact FROM customers WHERE name LIKE ? ORDER BY id"
                self.cursor.execute(query, ('%' + search_term + '%',))
            else:
                query = "SELECT id, name, email, contact FROM customers ORDER BY id"
                self.cursor.execute(query)

            customers = self.cursor.fetchall()
            for customer in customers:
                self.tree.insert('', tk.END, values=customer)
        finally:
            self.root.config(cursor="") # Reset to the default cursor

    def search_customers(self, event=None):
        """Filter the customer list based on the search entry."""
        search_term = self.search_entry.get().strip()
        self.load_customers(search_term)

    def sort_by_column(self, col, reverse):
        """Sort treeview data when a column header is clicked."""
        # Get data from all rows
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]

        # Determine sort order
        if col == self._last_sort_column:
            reverse = not self._last_sort_reverse
        else:
            reverse = False

        # If the column is 'id', sort numerically, otherwise sort as strings (case-insensitive)
        if col == 'id':
            data.sort(key=lambda t: int(t[0]), reverse=reverse)
        else:
            data.sort(key=lambda t: t[0].lower(), reverse=reverse)

        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)

        # Update heading to show sort direction
        self.tree.heading(col, text=col.capitalize(), command=lambda: self.sort_by_column(col, not reverse))

        self._last_sort_column = col
        self._last_sort_reverse = reverse

    def show_status(self, message, duration=4000):
        """Display a message in the status bar for a set duration."""
        self.status_bar.config(text=message)
        if self.status_timer:
            self.root.after_cancel(self.status_timer)
        self.status_timer = self.root.after(duration, self.clear_status)

    def clear_status(self):
        self.status_bar.config(text="Ready")

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
        self.show_status(f"Customer '{name}' added successfully.")
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
                self.show_status(f"Customer '{customer_name}' deleted successfully.")
                self.load_customers() # Refresh the list
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to delete customer: {e}")

    def open_edit_window(self, event=None):
        """Open a new window to edit the selected customer's details."""
        selected_item = self.tree.focus()
        if not selected_item:
            return  # No item selected

        customer_data = self.tree.item(selected_item, 'values')
        EditWindow(self, customer_data)

    def on_closing(self):
        """Handles the window closing event to safely close the DB connection."""
        self.conn.close()
        self.root.destroy()

class EditWindow(tk.Toplevel):
    """A Toplevel window for editing a customer's details."""
    def __init__(self, parent_app, customer_data):
        super().__init__(parent_app.root)
        self.parent_app = parent_app
        self.customer_id, old_name, old_email, old_contact = customer_data

        self.title("Edit Customer")
        self.transient(parent_app.root) # Keep this window on top of the main app
        self.grab_set() # Modal behavior: block interaction with the main window

        edit_frame = ttk.Frame(self, padding="10")
        edit_frame.pack(fill=tk.BOTH, expand=True)

        # Name
        ttk.Label(edit_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(edit_frame, width=40)
        self.name_entry.grid(row=0, column=1, pady=2)
        self.name_entry.insert(0, old_name)

        # Email
        ttk.Label(edit_frame, text="Email:").grid(row=1, column=0, sticky="w", pady=2)
        self.email_entry = ttk.Entry(edit_frame, width=40)
        self.email_entry.grid(row=1, column=1, pady=2)
        self.email_entry.insert(0, old_email)

        # Contact
        ttk.Label(edit_frame, text="Contact:").grid(row=2, column=0, sticky="w", pady=2)
        self.contact_entry = ttk.Entry(edit_frame, width=40)
        self.contact_entry.grid(row=2, column=1, pady=2)
        self.contact_entry.insert(0, old_contact)

        # Save Button
        save_button = ttk.Button(edit_frame, text="Save Changes", command=self.save_changes)
        save_button.grid(row=3, column=0, columnspan=2, pady=10)

    def save_changes(self):
        """Save the updated customer details to the database."""
        new_name = self.name_entry.get().strip()
        new_email = self.email_entry.get().strip()
        new_contact = self.contact_entry.get().strip()

        if not new_name:
            messagebox.showerror("Error", "Name is a required field!", parent=self)
            return

        try:
            cursor = self.parent_app.cursor
            cursor.execute("UPDATE customers SET name = ?, email = ?, contact = ? WHERE id = ?",
                                (new_name, new_email, new_contact, self.customer_id))
            self.parent_app.conn.commit()
            self.destroy()
            self.parent_app.show_status(f"Customer '{new_name}' updated successfully.")
            self.parent_app.load_customers()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update customer: {e}", parent=self)

if __name__ == "__main__":
    root = tk.Tk()
    app = BookkeepingApp(root)

    # Set the application icon
    icon_image = Image.open("icon.png") # Make sure you have an 'icon.png' file
    photo_image = ImageTk.PhotoImage(icon_image)
    root.iconphoto(False, photo_image)

    # Set the theme
    sv_ttk.set_theme("dark")

    root.mainloop()
