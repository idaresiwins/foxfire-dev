from fpdf import FPDF

def createInvoice(user, items, pickup, total, dt, comment):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.image("FoxyApp/static/Photos/sprouts.png", x=None, y=None, w=50, h=50, type='PNG', link='')
    pdf.cell(200, 10, txt=f'Invoice number: {user.id}{dt}',ln=1, align='C')
    pdf.cell(200, 10, txt='Customer Info:', ln=2, align='L')
    pdf.cell(200, 10, txt=f'Name: {user.name}', ln=3, align='L')
    pdf.cell(200, 10, txt=f'Phone: {user.phone}', ln=4, align='L')
    pdf.cell(200, 10, txt=f'Email: {user.email}', ln=5, align='L')
    pdf.cell(200, 10, txt=f' ', ln=6, align='L')
    pdf.cell(200, 10, txt=f'Items in order: ', ln=7, align='L')
    pdf.cell(200, 10, txt=f'{items}', ln=8, align='L')
    pdf.cell(200, 10, txt=f' ', ln=9, align='L')
    pdf.cell(200, 10, txt=f'Pickup location:', ln=10, align='L')
    pdf.cell(200, 10, txt=f'{pickup}', ln=11, align='L')
    pdf.cell(200, 10, txt=f'Comments:', ln=10, align='L')
    pdf.cell(200, 10, txt=f'{comment}', ln=11, align='L')
    pdf.cell(200, 10, txt=f'Customer total: ${total}', ln=12, align='L')
    pdf.output(f"FoxyApp/orderforms/{user.id}{dt}.pdf")

