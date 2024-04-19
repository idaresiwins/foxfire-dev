import gspread
from datetime import datetime
sa = gspread.service_account(filename="D:\\Downloads\\foxfire-helical-chemist-389721-702650f035f7.json")

sh = sa.open("Foxfire Farms KY (Responses)")
wks_order = sh.worksheet("Mock Orders Sheet")
wks_customer_details = sh.worksheet("Customer_Details")
wks_label = sh.worksheet("mock label orders")
def cycle(prods):
    dt = datetime.now().strftime("_%y%b%d-%f")
    wks_order = sh.worksheet("Mock Orders Sheet")
    wks_order.update_title(f"Archive{dt}")
    sh.add_worksheet(title="Mock Orders Sheet", rows=100, cols=200)
    wks_order = sh.worksheet("Mock Orders Sheet")
    wks_order.append_row(prods)