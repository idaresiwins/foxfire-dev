from fpdf import FPDF
from FoxyApp.foxfireutility import friday
from FoxyApp import app
import os
def createInvoice(user, items, pickup, total, dt, comment):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.image(os.path.join(app.root_path, "static/photos/sprouts.png"), x=None, y=None, w=50, h=50, type='PNG', link='')
    pdf.cell(200, 10, txt=f'Invoice number: {user.id}{dt}',ln=1, align='C')
    pdf.cell(200, 10, txt='Customer Info:', ln=2, align='L')
    pdf.cell(200, 10, txt=f'Name: {user.name}', ln=3, align='L')
    pdf.cell(200, 10, txt=f'Phone: {user.phone}', ln=4, align='L')
    pdf.cell(200, 10, txt=f'Email: {user.email}', ln=5, align='L')
    pdf.cell(200, 10, txt=f' ', ln=6, align='L')
    pdf.cell(200, 10, txt=f'Items in order: ', ln=7, align='L')
    pdf.multi_cell(200, 10, txt=f'{items}')
    pdf.cell(200, 10, txt=f' ', ln=9, align='L')
    pdf.cell(200, 10, txt=f'Pickup location:', ln=10, align='L')
    pdf.cell(200, 10, txt=f'{pickup}', ln=11, align='L')
    pdf.cell(200, 10, txt=f'Comments:', ln=10, align='L')
    pdf.cell(200, 10, txt=f'{comment}', ln=11, align='L')
    pdf.cell(200, 10, txt=f'Customer total: ${total}', ln=12, align='L')
    pdf.output(os.path.join(app.root_path, f"orderforms/{user.id}{dt}.pdf"))

def driver_sheet(orders):
    # Sorting the orders by pickup location (index 1 of the sublists)
    orders.sort(key=lambda x: x[1])
    # Calculate total and average
    total_amount = sum(float(order[2]) for order in orders if order[0] != "Name")
    average_amount = total_amount / len(orders) if orders else 0
    fri = friday()
    # Define class for PDF
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, f'Order List {fri}', 0, 1, 'C')

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    # Create instance of FPDF class & add a page
    pdf = PDF()
    pdf.add_page()

    # Column titles
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, 'Name', 1)
    pdf.cell(100, 10, 'Pickup Location', 1)
    pdf.cell(20, 10, 'Total', 1)
    pdf.cell(30, 10, 'Notes', 1, ln=1)

    # Add the orders to the PDF
    pdf.set_font('Arial', '', 12)
    for order in orders:
        if order[0] == "Name":
            continue
        else:
            pdf.cell(40, 10, order[0], 1)
            pdf.cell(100, 10, order[1], 1)
            pdf.cell(20, 10, order[2], 1)
            pdf.cell(30, 10, "", 1, ln=1)

    # Add total and average calculations to PDF
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(90, 10, 'Total Orders', 1)
    pdf.cell(30, 10, f'{len(orders)}', 1, ln=1)

    pdf.cell(90, 10, 'Total Amount', 1)
    pdf.cell(30, 10, f'${total_amount:.2f}', 1, ln=1)

    pdf.cell(90, 10, 'Average Order Cost', 1)
    pdf.cell(30, 10, f'${average_amount:.2f}', 1, ln=1)

    # Close previously opened PDF if exists
    if os.path.exists(os.path.join(app.root_path, 'static/orders.pdf')):
        os.remove(os.path.join(app.root_path, 'static/orders.pdf'))

    # Output the PDF to a file
    pdf.output(os.path.join(app.root_path, 'static/orders.pdf'), 'F')

    print("PDF created successfully!")
