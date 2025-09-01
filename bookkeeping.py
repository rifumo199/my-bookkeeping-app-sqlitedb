import sqlite3
import tkinter as tk
import csv
import json
from datetime import date, timedelta
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

        # Load window geometry
        self._load_geometry()

        # Create the menu bar
        self._create_menu()

        self.create_table()
        # Create UI widgets
        self.create_widgets()

        # Load initial data into the view
        self.load_customers()
        self.load_invoices()

        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_selected)

        # Ensure DB connection is closed when window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # For the Undo feature
        self._last_deleted_customer = None

    def create_table(self):
        """Create the tables if they don't already exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                contact TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                tax_amount REAL NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        # Add default tax rate if not present
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('tax_rate', '0.2')")
        self.conn.commit()

    def _create_menu(self):
        """Creates the main application menu bar."""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # File Menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        self.undo_menu_item_index = file_menu.index("end") # Placeholder for undo
        file_menu.add_command(label="Preferences...", command=self.open_preferences_window)
        file_menu.add_command(label="Export to CSV...", command=self.export_to_csv)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Help Menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_dialog)

    def show_about_dialog(self):
        """Displays the about dialog box."""
        messagebox.showinfo("About Bookkeeping App", "Bookkeeping App v1.0\n\nCreated by Oliver.")

    def create_widgets(self):
        """Create and layout the UI elements."""
        # --- Main container frame ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Create a Notebook (tabbed interface) ---
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # --- Create Customer Tab ---
        customer_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(customer_tab, text="Customers")

        self._create_input_frame(customer_tab)
        self._create_search_frame(customer_tab)
        self._create_treeview_frame(customer_tab)
        self._create_action_buttons(customer_tab)

        # --- Create Invoices Tab ---
        invoices_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(invoices_tab, text="Invoices")
        self._create_invoice_widgets(invoices_tab)


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

        # Bind right-click event for the context menu
        self.tree.bind("<Button-3>", self.show_context_menu)

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

    def _create_invoice_widgets(self, parent_frame):
        """Create and layout the UI elements for the invoices tab."""
        # --- Invoice List Frame (using Treeview) ---
        invoice_tree_frame = ttk.LabelFrame(parent_frame, text="Invoices", padding="10")
        invoice_tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('id', 'customer', 'invoice_date', 'due_date', 'total_amount', 'status')
        self.invoice_tree = ttk.Treeview(invoice_tree_frame, columns=columns, show='headings')

        # Define headings and column properties
        self.invoice_tree.heading('id', text='ID')
        self.invoice_tree.column('id', width=40, anchor=tk.CENTER)
        self.invoice_tree.heading('customer', text='Customer')
        self.invoice_tree.column('customer', width=150)
        self.invoice_tree.heading('invoice_date', text='Invoice Date')
        self.invoice_tree.column('invoice_date', width=100)
        self.invoice_tree.heading('due_date', text='Due Date')
        self.invoice_tree.column('due_date', width=100)
        self.invoice_tree.heading('total_amount', text='Total')
        self.invoice_tree.column('total_amount', width=80, anchor=tk.E)
        self.invoice_tree.heading('status', text='Status')
        self.invoice_tree.column('status', width=80, anchor=tk.CENTER)


        # Add a scrollbar
        scrollbar = ttk.Scrollbar(invoice_tree_frame, orient=tk.VERTICAL, command=self.invoice_tree.yview)
        self.invoice_tree.configure(yscroll=scrollbar.set)

        self.invoice_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Action Buttons ---
        invoice_actions_frame = ttk.Frame(parent_frame, padding="10")
        invoice_actions_frame.pack(fill=tk.X)
        
        ttk.Button(invoice_actions_frame, text="Create New Invoice", command=self.create_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(invoice_actions_frame, text="View/Edit Invoice", command=self.edit_invoice).pack(side=tk.LEFT, padx=5)
        ttk.Button(invoice_actions_frame, text="Delete Invoice", command=self.delete_invoice).pack(side=tk.LEFT, padx=5)

    def load_invoices(self):
        """Clear the treeview and load all invoices from the database."""
        self.root.config(cursor="watch") # Set a busy cursor
        self.root.update_idletasks() # Ensure cursor updates immediately
        try:
            # Clear existing items to prevent duplication
            for item in self.invoice_tree.get_children():
                self.invoice_tree.delete(item)

            # Fetch and display new data
            query = """
                SELECT i.id, c.name, i.invoice_date, i.due_date, i.total_amount, i.status
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                ORDER BY i.id
            """
            self.cursor.execute(query)

            invoices = self.cursor.fetchall()
            for invoice in invoices:
                self.invoice_tree.insert('', tk.END, values=invoice)
        finally:
            self.root.config(cursor="") # Reset to the default cursor

    def create_invoice(self):
        InvoiceWindow(self)

    def edit_invoice(self):
        selected_item = self.invoice_tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select an invoice to edit.")
            return
        invoice_id = self.invoice_tree.item(selected_item, 'values')[0]
        InvoiceWindow(self, invoice_id)

    def delete_invoice(self):
        selected_item = self.invoice_tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select an invoice to delete.")
            return
        
        invoice_id = self.invoice_tree.item(selected_item, 'values')[0]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete invoice ID: {invoice_id}?"):
            try:
                self.cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
                self.cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
                self.conn.commit()
                self.show_status(f"Invoice ID: {invoice_id} deleted successfully.")
                self.load_invoices()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to delete invoice: {e}")

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

    def export_to_csv(self):
        """Export the current customer list to a CSV file."""
        from tkinter import filedialog
        
        # Open a "save as" dialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Customers to CSV"
        )

        if not file_path:
            return # User cancelled the dialog

        try:
            self.cursor.execute("SELECT id, name, email, contact FROM customers ORDER BY name")
            customers = self.cursor.fetchall()
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Name', 'Email', 'Contact']) # Write header
                writer.writerows(customers) # Write data
            self.show_status(f"Successfully exported {len(customers)} customers to {file_path}")
        except (IOError, sqlite3.Error) as e:
            messagebox.showerror("Export Error", f"Failed to export data: {e}")

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
            # Store the customer data before deleting for the undo feature
            self._last_deleted_customer = {
                'id': customer_id,
                'name': customer_name,
                'email': customer_data[2],
                'contact': customer_data[3]
            }

            try:
                self.cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
                self.conn.commit()
                self.show_status(f"Customer '{customer_name}' deleted successfully.")
                self.load_customers() # Refresh the list
                self._add_undo_option()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Failed to delete customer: {e}")

    def _add_undo_option(self):
        """Adds an 'Undo Delete' option to the File menu."""
        file_menu = self.root.nametowidget(self.root.cget("menu")).winfo_children()[0]
        file_menu.insert_command(self.undo_menu_item_index, label="Undo Delete", command=self.undo_delete)

    def open_edit_window(self, event=None):
        """Open a new window to edit the selected customer's details."""
        selected_item = self.tree.focus()
        if not selected_item:
            return  # No item selected

        customer_data = self.tree.item(selected_item, 'values')
        EditWindow(self, customer_data)

    def undo_delete(self):
        """Re-inserts the last deleted customer into the database."""
        if self._last_deleted_customer:
            customer = self._last_deleted_customer
            try:
                self.cursor.execute("INSERT INTO customers (id, name, email, contact) VALUES (?, ?, ?, ?)",
                                    (customer['id'], customer['name'], customer['email'], customer['contact']))
                self.conn.commit()
                self.show_status(f"Restored customer '{customer['name']}'.")
                self.load_customers()
                self._last_deleted_customer = None
                # Remove the 'Undo' option from the menu
                file_menu = self.root.nametowidget(self.root.cget("menu")).winfo_children()[0]
                file_menu.delete("Undo Delete")
            except sqlite3.Error as e:
                messagebox.showerror("Undo Error", f"Failed to restore customer: {e}")

    def show_context_menu(self, event):
        """Display a right-click context menu on the treeview."""
        # Identify the item that was right-clicked
        item_id = self.tree.identify_row(event.y)

        if item_id:
            # Select the right-clicked item
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)

            # Create a context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Edit Customer", command=self.open_edit_window)
            context_menu.add_command(label="Delete Customer", command=self.delete_customer)
            
            # Display the menu at the cursor's position
            context_menu.tk_popup(event.x_root, event.y_root)

    def on_tab_selected(self, event):
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0: # Customer tab
            self.load_customers()
        elif selected_tab == 1: # Invoices tab
            self.load_invoices()

    def open_preferences_window(self):
        """Opens the preferences window."""
        PreferencesWindow(self)

    def on_closing(self):
        """Handles the window closing event to save geometry and close the DB connection."""
        self._save_geometry()
        self.conn.close()
        self.root.destroy()

    def _save_geometry(self):
        """Saves the current window size and position to a config file."""
        try:
            with open("config.json", "w") as f:
                config = {"geometry": self.root.geometry(), "theme": sv_ttk.get_theme()}
                json.dump(config, f, indent=4)
        except IOError as e:
            print(f"Warning: Could not save window geometry: {e}")

    def _load_geometry(self):
        """Loads the window size and position from a config file."""
        try:
            with open("config.json", "r") as f: 
                config = json.load(f)
                self.root.geometry(config["geometry"])
                sv_ttk.set_theme(config.get("theme", "dark"))
        except (IOError, json.JSONDecodeError, KeyError):
            # File doesn't exist, is corrupt, or key is missing. Use default size.
            sv_ttk.set_theme("dark")

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

class PreferencesWindow(tk.Toplevel):
    """A Toplevel window for application preferences."""
    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.parent_app = parent_app

        self.title("Preferences")
        self.transient(parent_app.root)
        self.grab_set()

        frame = ttk.Frame(self, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Theme:").pack(pady=(0, 5))

        ttk.Button(frame, text="Set Light Theme", command=lambda: self.set_theme("light")).pack(fill=tk.X, pady=2)
        ttk.Button(frame, text="Set Dark Theme", command=lambda: self.set_theme("dark")).pack(fill=tk.X, pady=2)

        ttk.Label(frame, text="Tax Rate (%):").pack(pady=(10, 5))
        self.tax_rate_entry = ttk.Entry(frame)
        self.tax_rate_entry.pack(fill=tk.X, pady=2)
        self.load_tax_rate()

        save_button = ttk.Button(frame, text="Save Preferences", command=self.save_preferences)
        save_button.pack(pady=10)

    def set_theme(self, theme_name):
        sv_ttk.set_theme(theme_name)
        self.parent_app.show_status(f"Theme changed to {theme_name}. Restart app for full effect.")

    def load_tax_rate(self):
        self.parent_app.cursor.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
        tax_rate = float(self.parent_app.cursor.fetchone()[0]) * 100
        self.tax_rate_entry.insert(0, f"{tax_rate:.2f}")

    def save_preferences(self):
        try:
            tax_rate = float(self.tax_rate_entry.get()) / 100
            self.parent_app.cursor.execute("UPDATE settings SET value = ? WHERE key = ?", (str(tax_rate), 'tax_rate'))
            self.parent_app.conn.commit()
            self.parent_app.show_status("Preferences saved successfully.")
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid tax rate. Please enter a number.", parent=self)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save preferences: {e}", parent=self)

class InvoiceWindow(tk.Toplevel):
    """A Toplevel window for creating and editing an invoice."""
    def __init__(self, parent_app, invoice_id=None):
        super().__init__(parent_app.root)
        self.parent_app = parent_app
        self.invoice_id = invoice_id

        self.title("Create New Invoice" if not invoice_id else f"Edit Invoice #{invoice_id}")
        self.transient(parent_app.root)
        self.grab_set()

        # --- Main Frame ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Customer and Dates Frame ---
        info_frame = ttk.LabelFrame(main_frame, text="Invoice Details", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # Customer
        ttk.Label(info_frame, text="Customer:").grid(row=0, column=0, sticky="w", pady=2)
        self.customer_var = tk.StringVar()
        self.customer_menu = ttk.Combobox(info_frame, textvariable=self.customer_var, state="readonly")
        self.customer_menu.grid(row=0, column=1, sticky="we", pady=2)
        self.customers = self.load_customer_list()

        # Invoice Date
        ttk.Label(info_frame, text="Invoice Date:").grid(row=1, column=0, sticky="w", pady=2)
        self.invoice_date_entry = ttk.Entry(info_frame)
        self.invoice_date_entry.grid(row=1, column=1, sticky="we", pady=2)
        self.invoice_date_entry.insert(0, date.today().strftime('%Y-%m-%d'))

        # Due Date
        ttk.Label(info_frame, text="Due Date:").grid(row=2, column=0, sticky="w", pady=2)
        self.due_date_entry = ttk.Entry(info_frame)
        self.due_date_entry.grid(row=2, column=1, sticky="we", pady=2)
        self.due_date_entry.insert(0, (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'))

        # --- Invoice Items Frame ---
        items_frame = ttk.LabelFrame(main_frame, text="Invoice Items", padding="10")
        items_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ('description', 'quantity', 'unit_price', 'total')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings')
        self.items_tree.heading('description', text='Description')
        self.items_tree.heading('quantity', text='Quantity')
        self.items_tree.heading('unit_price', text='Unit Price')
        self.items_tree.heading('total', text='Total')
        self.items_tree.pack(fill=tk.BOTH, expand=True)

        # --- Totals Frame ---
        totals_frame = ttk.Frame(main_frame, padding="10")
        totals_frame.pack(fill=tk.X)

        ttk.Label(totals_frame, text="Subtotal:").grid(row=0, column=0, sticky="e")
        self.subtotal_label = ttk.Label(totals_frame, text="0.00")
        self.subtotal_label.grid(row=0, column=1, sticky="w")

        ttk.Label(totals_frame, text="Tax:").grid(row=1, column=0, sticky="e")
        self.tax_label = ttk.Label(totals_frame, text="0.00")
        self.tax_label.grid(row=1, column=1, sticky="w")

        ttk.Label(totals_frame, text="Total:").grid(row=2, column=0, sticky="e")
        self.total_label = ttk.Label(totals_frame, text="0.00")
        self.total_label.grid(row=2, column=1, sticky="w")

        # --- Action Buttons ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="Add Item", command=self.add_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Remove Item", command=self.remove_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Save Invoice", command=self.save_invoice).pack(side=tk.RIGHT, padx=5)

        if self.invoice_id:
            self.load_invoice_data()

    def load_customer_list(self):
        self.parent_app.cursor.execute("SELECT id, name FROM customers ORDER BY name")
        customers = self.parent_app.cursor.fetchall()
        self.customer_menu['values'] = [f"{name} (ID: {cid})" for cid, name in customers]
        return {cid: name for cid, name in customers}

    def load_invoice_data(self):
        self.parent_app.cursor.execute("SELECT customer_id, invoice_date, due_date FROM invoices WHERE id = ?", (self.invoice_id,))
        customer_id, invoice_date, due_date = self.parent_app.cursor.fetchone()

        self.customer_var.set(f"{self.customers[customer_id]} (ID: {customer_id})")
        self.invoice_date_entry.delete(0, tk.END)
        self.invoice_date_entry.insert(0, invoice_date)
        self.due_date_entry.delete(0, tk.END)
        self.due_date_entry.insert(0, due_date)

        self.parent_app.cursor.execute("SELECT description, quantity, unit_price FROM invoice_items WHERE invoice_id = ?", (self.invoice_id,))
        for item in self.parent_app.cursor.fetchall():
            description, quantity, unit_price = item
            total = quantity * unit_price
            self.items_tree.insert('', tk.END, values=(description, quantity, unit_price, f"{total:.2f}"))
        self.update_totals()

    def add_item(self):
        AddItemWindow(self)

    def remove_item(self):
        selected_item = self.items_tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select an item to remove.", parent=self)
            return
        self.items_tree.delete(selected_item)
        self.update_totals()

    def update_totals(self):
        subtotal = 0
        for item_id in self.items_tree.get_children():
            item = self.items_tree.item(item_id, 'values')
            subtotal += float(item[3])

        self.parent_app.cursor.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
        tax_rate = float(self.parent_app.cursor.fetchone()[0])
        
        tax = subtotal * tax_rate
        total = subtotal + tax

        self.subtotal_label.config(text=f"{subtotal:.2f}")
        self.tax_label.config(text=f"{tax:.2f}")
        self.total_label.config(text=f"{total:.2f}")

    def save_invoice(self):
        customer_str = self.customer_var.get()
        if not customer_str:
            messagebox.showerror("Error", "Please select a customer.", parent=self)
            return
        
        customer_id = int(customer_str.split("(ID: ")[1][:-1])
        invoice_date = self.invoice_date_entry.get()
        due_date = self.due_date_entry.get()
        
        items = []
        for item_id in self.items_tree.get_children():
            items.append(self.items_tree.item(item_id, 'values'))

        if not items:
            messagebox.showerror("Error", "Please add at least one item to the invoice.", parent=self)
            return

        subtotal = sum(float(item[3]) for item in items)
        
        self.parent_app.cursor.execute("SELECT value FROM settings WHERE key = 'tax_rate'")
        tax_rate = float(self.parent_app.cursor.fetchone()[0])
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount

        try:
            if self.invoice_id:
                # Update existing invoice
                self.parent_app.cursor.execute("""
                    UPDATE invoices 
                    SET customer_id = ?, invoice_date = ?, due_date = ?, total_amount = ?, tax_amount = ?, status = ?
                    WHERE id = ?
                """, (customer_id, invoice_date, due_date, total_amount, tax_amount, "Draft", self.invoice_id))
                self.parent_app.cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (self.invoice_id,))
                invoice_id = self.invoice_id
            else:
                # Insert new invoice
                self.parent_app.cursor.execute("""
                    INSERT INTO invoices (customer_id, invoice_date, due_date, total_amount, tax_amount, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (customer_id, invoice_date, due_date, total_amount, tax_amount, "Draft"))
                invoice_id = self.parent_app.cursor.lastrowid

            # Insert invoice items
            for item in items:
                description, quantity, unit_price, _ = item
                self.parent_app.cursor.execute("""
                    INSERT INTO invoice_items (invoice_id, description, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                """, (invoice_id, description, quantity, unit_price))

            self.parent_app.conn.commit()
            self.parent_app.load_invoices()
            self.parent_app.show_status("Invoice saved successfully.")
            self.destroy()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to save invoice: {e}", parent=self)

class AddItemWindow(tk.Toplevel):
    """A Toplevel window for adding a new item to an invoice."""
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window

        self.title("Add Invoice Item")
        self.transient(parent_window)
        self.grab_set()

        item_frame = ttk.Frame(self, padding="10")
        item_frame.pack(fill=tk.BOTH, expand=True)

        # Description
        ttk.Label(item_frame, text="Description:").grid(row=0, column=0, sticky="w", pady=2)
        self.description_entry = ttk.Entry(item_frame, width=40)
        self.description_entry.grid(row=0, column=1, pady=2)

        # Quantity
        ttk.Label(item_frame, text="Quantity:").grid(row=1, column=0, sticky="w", pady=2)
        self.quantity_entry = ttk.Entry(item_frame, width=40)
        self.quantity_entry.grid(row=1, column=1, pady=2)

        # Unit Price
        ttk.Label(item_frame, text="Unit Price:").grid(row=2, column=0, sticky="w", pady=2)
        self.unit_price_entry = ttk.Entry(item_frame, width=40)
        self.unit_price_entry.grid(row=2, column=1, pady=2)

        # Add Button
        add_button = ttk.Button(item_frame, text="Add Item", command=self.add_item_to_invoice)
        add_button.grid(row=3, column=0, columnspan=2, pady=10)

    def add_item_to_invoice(self):
        description = self.description_entry.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        unit_price_str = self.unit_price_entry.get().strip()

        if not all([description, quantity_str, unit_price_str]):
            messagebox.showerror("Error", "All fields are required!", parent=self)
            return

        try:
            quantity = float(quantity_str)
            unit_price = float(unit_price_str)
        except ValueError:
            messagebox.showerror("Error", "Quantity and Unit Price must be numbers!", parent=self)
            return

        total = quantity * unit_price
        self.parent_window.items_tree.insert('', tk.END, values=(description, quantity, unit_price, f"{total:.2f}"))
        self.parent_window.update_totals()
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Hide the root window initially to prevent flashing
    root.withdraw()

    app = BookkeepingApp(root)

    # Set the application icon (ensure icon.png is in the project directory)
    try:
        icon_image = Image.open("icon.png")
        photo_image = ImageTk.PhotoImage(icon_image)
        root.iconphoto(False, photo_image)
    except FileNotFoundError:
        print("Warning: icon.png not found. Skipping icon setup.")

    # Make the window visible now that it's fully configured
    root.deiconify()
    root.mainloop()
