from calendar import monthrange
import datetime
from fpdf import FPDF
from matplotlib.dates import DateFormatter,HourLocator
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd

RAW_DIRECTORY = os.path.join(os.path.abspath(''),"0-RawData")
PROCESSED_DIRECTORY = os.path.join(os.path.abspath(''),"1-Invoices")
PROCESSED_HOURS_DIRECTORY = os.path.join(os.path.abspath(''),"2-ProcessedHours")
DAYS = ['Monday','Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

class PDF(FPDF):
    """
    Custom PDF class inheriting from FPDF for generating PDF files.
    This class overrides the default header and footer methods of FPDF to provide a custom header and footer.
    """

    # Uncommented and added docstring for header
    # def header(self):
    #     """
    #     Overrides the default header method to set a custom header for the PDF.
    #     Sets the font to Arial bold with size 15 and displays the title in the center.
    #     """
    #     # Arial bold 15
    #     self.set_font('Arial', 'B', 15)
    #     # Move to the right
    #     self.cell(80)
    #     # Title
    #     self.cell(30, 10, 'Title', 1, 0, 'C')
    #     # Line break
    #     self.ln(20)

    def footer(self):
        """
        Overrides the default footer method to set a custom footer for the PDF.
        Sets the font to Arial italic with size 8 and displays the page number in the center.
        """
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')


def add_day_when_end_is_next_day(x):
    """
    Adjusts the 'End' field if it's earlier than the 'Begin' field by adding one day.
    
    Parameters:
    - x (dict): Dictionary containing 'Begin', 'End', and 'Date' keys.

    Returns:
    - dict: Updated dictionary with corrected 'End' date-time.
    """
    if (x['Begin'] > x['End']):
        x['End'] = x['Date'] + x['End'] + np.timedelta64(1, 'D')
    else:
        x['End'] = x['End'] + x['Date']
    
    return x  

def extract_worked_hour_as_df(month,year,company_name,drop_date_from_beginning_end=True):
    """
    Extracts worked hours from a CSV file and returns a DataFrame with the relevant details.

    Parameters:
    - month (int or str): The month for which data is to be extracted.
    - year (int): The year for which data is to be extracted.
    - company_name (str): The name of the company, used in the filename.
    - drop_date_from_beginning_end (bool): Whether to drop the date part from 'Begin' and 'End' columns. Default is True.

    Returns:
    - df (pd.DataFrame): DataFrame with the worked hours.
    - total_hours (str): The total hours worked in "HH:MM" format.
    """

    # Add zero to single digit months
    if len(str(month))==1:
        month = '0'+str(month)

    # Import the file
    df = pd.read_csv(os.path.join(RAW_DIRECTORY,f'{company_name}_{month}{year}.csv'))
    
    # Get the file language
    if df.columns[0] == 'Datum':
        file_language = 'German'
    elif df.columns[0] == 'Fecha':
        file_language = 'Spanish'
    else:
        file_language = 'Engish'
    
    # Remove the last row with the months total hours 
    df.drop(index=df.index[-1], axis=0,inplace=True)

    # Rename the columns
    df.columns = ['Date', 'Begin', 'End', 'Hours','Pause','Notes']

    # Convert the date column to datetime
    df['Date']=df['Date'].apply(get_datetime_object_from_date,args=(month,year,file_language,))

    # Add date to beginning and end (Consider when the end date is the next day)
    df['End']=pd.to_timedelta((df['End'].str.split(':', expand=True).astype(int) * (60, 1)).sum(axis=1), unit='min')
    df['Begin']=pd.to_timedelta((df['Begin'].str.split(':', expand=True).astype(int) * (60, 1)).sum(axis=1), unit='min')
    df = df.apply(lambda x: add_day_when_end_is_next_day(x), axis=1)
    df['Begin'] = df['Date']+df['Begin'] 

    # Recalculate hours and extract only hours as strings
    df['Hours'] = df['End']-df['Begin']
    total_hours = df['Hours'].sum().total_seconds()
    hours_part = int(total_hours//3600)
    minutes_part = int(total_hours%3600//60)
    if len(str(minutes_part))==1:
        minutes_part = '0'+str(minutes_part)
    total_hours = f'{hours_part}:{minutes_part}'

    df['Hours']=df['Hours'].apply(get_hhmm_from_timedelta)
    
    if drop_date_from_beginning_end:
        df['Begin'] = df['Begin'].dt.strftime("%H:%M")
        df['End'] = df['End'].dt.strftime("%H:%M")
    
#     df['Notes'] = df.apply(lambda row : shorten_string(row['Notes'],40), axis = 1)
    return df,total_hours

def get_datetime_object_from_date(date_str,month,year,file_language):
    """
    Convert a date string to a datetime object based on the given language.

    Parameters:
    - date_str (str): The date string to be converted.
    - month (int): The month.
    - year (int): The year.
    - file_language (str): The language of the date string (one of 'German', 'English', 'Spanish').

    Returns:
    - datetime.datetime: The converted datetime object.
    """

    date_str_list=date_str.split()
    if file_language == 'German':
        if int(month)!=5:
            date_time = datetime.datetime(year, int(get_month_number_from_DE_string(date_str_list[1][:-1])), int(date_str_list[-1]))
        else:
            date_time = datetime.datetime(year, int(get_month_number_from_DE_string(date_str_list[1])), int(date_str_list[-1]))
    elif file_language == 'English':
        date_time = datetime.datetime(year, int(get_month_number_from_EN_string(date_str_list[1])), int(date_str_list[-1]))
    elif file_language == 'Spanish':
        date_time = datetime.datetime(year, int(get_month_number_from_ES_string(date_str_list[1])), int(date_str_list[-1]))

    return date_time

def get_month_number_from_DE_string(month_str):
    """
    Convert a German month abbreviation to its respective month number.

    Parameters:
    - month_str (str): German month abbreviation.

    Returns:
    - str: Month number as a string in "MM" format.
    """
    MONTHS_DE={'Jan':'01','Feb':'02','Mär':'03','Apr':'04','Mai':'05','Jun':'06','Jul':'07','Aug':'08','Sept':'09','Okt':'10','Nov':'11','Dez':'12'}
    return MONTHS_DE[month_str]

def get_month_number_from_EN_string(month_str):
    """
    Convert an English month abbreviation to its respective month number.

    Parameters:
    - month_str (str): English month abbreviation.

    Returns:
    - str: Month number as a string in "MM" format.
    """
    MONTHS_DE={'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
    return MONTHS_DE[month_str]

def get_month_number_from_ES_string(month_str):
    """
    Convert a Spanish month abbreviation to its respective month number.

    Parameters:
    - month_str (str): Spanish month abbreviation.

    Returns:
    - str: Month number as a string in "MM" format.
    """
    MONTHS_DE={'ene.':'01','feb.':'02','mar.':'03','abr.':'04','may.':'05','jun':'06','jul':'07','ago.':'08','sep.':'09','oct.':'10','nov.':'11','dic.':'12'}
    return MONTHS_DE[month_str]

def get_hhmm_from_timedelta(timedelta_str):
    """
    Convert a timedelta string to "HH:MM" format.

    Parameters:
    - timedelta_str (str): The timedelta string to be converted.

    Returns:
    - str: Time in "HH:MM" format.
    """
    x = str(timedelta_str).split(':')
    x=x[0][-2:]+':'+x[1]
    return x

def get_wk_nb(datetime_object):
    """
    Get the week number from a datetime object.

    Parameters:
    - datetime_object (datetime.datetime): The datetime object.

    Returns:
    - int: Week number.
    """
    return datetime_object.isocalendar()[1]

def generate_and_save_pdf(df,month,year,total_hours,company_data={},employee_data={}):
    """
    Generates and saves a PDF file based on the given data.

    Parameters:
    - df (pd.DataFrame): DataFrame containing the work hours data with columns: 'Date', 'Begin', 'End', 'Hours', and 'Notes'.
    - month (str or int): The month for which the report is generated.
    - year (int): The year for which the report is generated.
    - total_hours (str): Total hours worked in the format 'HH:MM'.
    - company_data (dict, optional): Dictionary containing company information. Expected keys: 'name'.
    - employee_data (dict, optional): Dictionary containing employee details. Expected keys: 'name', 'position', 'email', and 'initials'.

    Description:
    The function generates a detailed hour report in PDF format for an employee for a specific month and year. The PDF includes:
    - Report header
    - Company name
    - Report dates
    - Employee details
    - Table containing the date, start time, end time, hours worked, and notes for each day.
    - Total hours worked in the month.

    The generated PDF is saved with a filename based on the employee's initials, month, and year in the PROCESSED_HOURS_DIRECTORY.

    Returns:
    None. Saves the generated PDF file to disk.
    """
    
    df=df.iloc[::-1]
    
    pdf = PDF()
    pdf.alias_nb_pages()

    pdf.add_page()
    pdf.set_xy(0, 0)

    turn_on_border=False # For troubleshooting
    
    #dates
    start_date = datetime.date(year,int(month),1)
    end_date = datetime.date(year,int(month),monthrange(year,int(month))[1])

    # Header
    pdf.set_font('arial', 'B', 22)

    pdf.cell(1,15,border=turn_on_border,ln=1)
    pdf.cell(190,10,f'Hour report',turn_on_border,1,'C')

    # Line
    pdf.set_fill_color(0, 0, 0)
    pdf.cell(190, 2, "", 0, 2, 'C',True)
    pdf.cell(10, 5, "", turn_on_border, 2, 'C',False) # Spacing

    # Company name
    pdf.set_font('arial', 'B', 13)
    pdf.cell(40,5,"Company name: ",turn_on_border,0,'L')
    pdf.set_font('arial', '', 13)
    pdf.cell(15,5,company_data['name'],turn_on_border,1,'L')

    # Dates of file
    pdf.set_font('arial', 'B', 13)
    pdf.cell(18,5,"Month: ",turn_on_border,0,'L')
    pdf.set_font('arial', '', 13)
    pdf.cell(15,5,start_date.strftime("%B"),turn_on_border,1,'L')

    # Employee data
    pdf.set_font('arial', '', 12)
    pdf.cell(190,5,employee_data['name'],turn_on_border,1,'R')
    pdf.cell(190,5,employee_data['position'],turn_on_border,1,'R')
    pdf.cell(190,5,employee_data['email'],turn_on_border,1,'R')
    pdf.cell(10, 20, "", turn_on_border, 1, 'C',False)

    # Data of report
    pdf.set_font('arial', 'B', 13)
    pdf.cell(140,5,"From: ",turn_on_border,0,'R')
    pdf.set_font('arial', '', 12)
    pdf.cell(50,5,start_date.strftime("%d %B, %Y"),turn_on_border,1,'R')
    pdf.set_font('arial', 'B', 13)
    pdf.cell(140,5,"To: ",turn_on_border,0,'R')
    pdf.set_font('arial', '', 12)
    pdf.cell(50,5,end_date.strftime("%d %B, %Y"),turn_on_border,1,'R')
    pdf.set_font('arial', 'B', 13)
    pdf.cell(140,5,f'Date of report:',turn_on_border,0,'R')
    pdf.set_font('arial', '', 12)
    pdf.cell(50,5,datetime.datetime.today().strftime("%d %B, %Y"),turn_on_border,1,'R')


    # Spacing
    pdf.cell(5, 10, "", turn_on_border, 1, 'C',False)

    # Week numbers:
    pdf.cell(10)
    pdf.set_font('arial', '', 15)
    pdf.cell(10, 5,f'Weeks: #{ start_date.isocalendar()[1]} - { end_date.isocalendar()[1]}', turn_on_border, 1, 'L',False)
    pdf.cell(1,5,border=turn_on_border,ln=1)

    # -------------------------Begin Table-------------------------
    table_spacing = 5
    hour_cell_spacing=15
    
    # Headers
    pdf.set_font('arial', 'B', 14)
    pdf.set_text_color(255,255,255) 
    pdf.set_fill_color(0, 0,0)
    header_row_height = 6
    pdf.cell(table_spacing,border=turn_on_border,ln=0)
    pdf.cell(20, header_row_height, 'Date', 1, 0, 'C',True)
    pdf.cell(hour_cell_spacing, header_row_height, 'Begin', 1, 0, 'C',True)
    pdf.cell(hour_cell_spacing, header_row_height, 'End', 1, 0, 'C',True)
    pdf.cell(hour_cell_spacing, header_row_height, 'Hours', 1, 0, 'C',True)
    pdf.cell(120, header_row_height, 'Task', 1, 1, 'C',True)
    pdf.set_text_color(0,0,0)    

    # Contents
    pdf.set_font('arial', '', 11)
    pdf.set_fill_color(220, 220, 220)

    for i in range(0, len(df)):
        cell_filled = i%2
        
        #Get length of the notes column string to get the height of the row
        if not (type(df['Notes'].iat[i])==float):
            row_height = 10 if len(df['Notes'].iat[i])>70 else 5
        else:
            df.iloc[i,df.columns.get_loc('Notes')] = ''
            row_height = 5

        # spacing
        pdf.cell(table_spacing,border=turn_on_border,ln=0)
        pdf.cell(20, row_height, f'{df["Date"].iloc[i].date().strftime("%d %B")[:7]}', 0, 0, 'C',fill=cell_filled)
        pdf.cell(hour_cell_spacing, row_height, f'{df["Begin"].iloc[i]}', 0, 0, 'C',fill=cell_filled)
        pdf.cell(hour_cell_spacing, row_height, f'{str(df["End"].iloc[i])}', 0, 0, 'C',fill=cell_filled)
        pdf.cell(hour_cell_spacing, row_height, f'{str(df["Hours"].iloc[i])}', 0, 0, 'C',fill=cell_filled)
        pdf.multi_cell(120, 5, f'{df["Notes"].iat[i]}',border= 0,align= 'L',fill=cell_filled)

    pdf.set_font('arial', 'B', 13)
    pdf.cell(table_spacing,border=turn_on_border,ln=0)

    pdf.cell(50,10,"Total time:",turn_on_border,0,'R')
    pdf.set_font('arial', '', 11)

    pdf.cell(hour_cell_spacing,10,total_hours,border=turn_on_border,ln=1)
    pdf.cell(20,20,border=turn_on_border,ln=1)
    # -------------------------End Table-------------------------
    
    pdf.set_font('arial', 'B', 13)
    pdf.cell(160,5,f'Worked hours:',turn_on_border,0,'R')
    pdf.set_font('arial', '', 12)
    pdf.cell(30,5,total_hours[:-2]+'00',turn_on_border,1,'R')

    pdf.cell(20,30,border=turn_on_border,ln=1)

#     # Line
    pdf.set_fill_color(0, 0, 0)
    pdf.cell(190, 2, "", 0, 2, 'C',True)
    save_file_name = os.path.join(PROCESSED_HOURS_DIRECTORY,f'{employee_data["initials"]}_{start_date.strftime("%B")}_{year}.pdf')
    pdf.output(save_file_name, 'F')

def generate_table_and_save_pdf(df,month,year,gbp_to_usd_rate,usd_pay,
                                company_data={},
                                employee_data={}):
    """
    Generate a PDF invoice from provided data and save it to a predefined directory.

    Parameters:
    - df (pandas.DataFrame): The data frame containing the transaction details with columns:
        * QTY: Quantity of the product/service
        * DESCRIPTION: Description of the product/service
        * UNIT PRICE: Price per unit of the product/service
        * AMOUNT: Total amount for the respective product/service
    - month (int): Month for which the invoice is being generated.
    - year (int): Year for which the invoice is being generated.
    - gbp_to_usd_rate (float): The conversion rate from GBP to USD.
    - usd_pay (float): The total amount payable in USD.
    - company_data (dict, optional): Dictionary containing the billing company's details. Expected keys:
        * name: Name of the company
        * street, street_cont: Address lines of the company
        * city: City of the company
        * postcode: Postcode of the company
    - employee_data (dict, optional): Dictionary containing the employee's details for the header and bank details sections. Expected keys:
        * name: Name of the employee
        * street: Address line of the employee
        * city, state, postcode: City, state, and postcode of the employee
        * country: Country of the employee
        * phone: Mobile number of the employee
        * bank_name, bank_address, holder_name, swift, routing_nb, account_nb: Bank details of the employee

    Outputs:
    - A PDF file saved in the PROCESSED_DIRECTORY with the filename format: 'year-month-company_name.pdf'.
    
    Notes:
    - This function assumes the existence of a PDF class for PDF generation.
    - The function also assumes that the PROCESSED_DIRECTORY is predefined.
    - Additional libraries/modules required: os, datetime, monthrange (from calendar)
    """
    df=df.iloc[::-1]
    
    pdf = PDF()
    pdf.alias_nb_pages()

    pdf.add_page()
    pdf.set_xy(0, 0)

    turn_on_border=False # For troubleshooting
            
    #dates
    start_date = datetime.date(year,int(month),1)
    end_date = datetime.date(year,int(month),monthrange(year,int(month))[1])
    invoice_date = datetime.datetime.today().strftime("%d/%m/%Y")
    due_date  = datetime.datetime.today() + datetime.timedelta(30)
    if len(str(month))==1:
        month = '0'+str(month)
    
    # Header spacing
    pdf.set_font('arial', 'B', 18)
    pdf.cell(1,15,border=turn_on_border,ln=1)
    pdf.cell(190,10,'',turn_on_border,1,'C')

    # Header
    pdf.set_fill_color(120, 194, 100)
    pdf.set_text_color(255,255,255) 
    pdf.cell(160, 10, f"{employee_data['name']}", 0, 0, 'L',True)
    pdf.cell(30, 10, f"INVOICE", 0, 1, 'R',True)
    pdf.cell(10, 5, "", turn_on_border, 2, 'C',False) # Spacing
    pdf.set_text_color(0,0,0) 

    # Employee adress
    pdf.set_font('arial', '', 13)
    pdf.cell(40,5,f"{employee_data['street']}",turn_on_border,2,'L')
    pdf.cell(40,5,f"{employee_data['city']}, {employee_data['state']} {employee_data['postcode']}",turn_on_border,2,'L')
    pdf.cell(40,5,f"{employee_data['country']}",turn_on_border,2,'L')
    pdf.cell(40,5,f"Mobile: {employee_data['phone']}",turn_on_border,2,'L')

    # Spacing
    pdf.cell(1,21,'',turn_on_border,1,'R')

    # Bill to and invoice info
    pdf.set_font('arial', 'B', 13)
    pdf.cell(40,5,"Bill To ",turn_on_border,0,'L')
    pdf.cell(120,5,"Invoice #:",turn_on_border,0,'R')
    pdf.set_font('arial', '', 12)
    pdf.cell(30,5,f"{year}-{month}",turn_on_border,1,"R")
    pdf.cell(40,5,f'{company_data["name"]}',turn_on_border,0,'L')
    pdf.set_font('arial', 'B', 13)
    pdf.cell(120,5,"Invoice Date:",turn_on_border,0,'R')
    pdf.set_font('arial', '', 12)
    pdf.cell(30,5,invoice_date,turn_on_border,1,"R")
    pdf.cell(40,5,f'{company_data["street"]}',turn_on_border,0,'L')
    pdf.set_font('arial', 'B', 13)
    pdf.cell(120,5,"Due Date:",turn_on_border,0,'R')
    pdf.set_font('arial','', 12)
    pdf.cell(30,5,due_date.strftime("%d/%m/%Y"),turn_on_border,1,'R')
    pdf.cell(40,5,f'{company_data["street_cont"]}',turn_on_border,1,'L')
    pdf.cell(40,5,f'{company_data["city"]}',turn_on_border,1,'L')
    pdf.cell(40,5,f'{company_data["postcode"]}',turn_on_border,2,'L')

    # Spacing
    pdf.cell(2, 10, "", turn_on_border, 1, 'C',False)

    # -------------------------Begin Table-------------------------
    table_spacing = 0.1
    hour_cell_spacing=35
    background_fill = (240,240,220)
    last_column_width = 34
    
    # Headers
    pdf.set_font('arial', 'B', 12)
    pdf.set_text_color(0,0,0) 
    pdf.set_fill_color(background_fill[0],background_fill[1],background_fill[2])
    header_row_height = 9
    pdf.cell(table_spacing,border=turn_on_border,ln=0)
    pdf.cell(20, header_row_height, 'QTY', 1, 0, 'C',True)
    pdf.cell(105, header_row_height, 'DESCRIPTION', 1, 0, 'C',True)
    pdf.cell(30, header_row_height, 'UNIT PRICE', 1, 0, 'C',True)
    pdf.cell(last_column_width, header_row_height, 'AMOUNT', 1, 1, 'C',True)
    pdf.set_text_color(0,0,0)    

    # Contents
    pdf.set_font('arial', '', 11)

    for i in range(0, len(df)):
        cell_filled = i%2
        row_height = 7
        
        # spacing
        pdf.cell(table_spacing,border=turn_on_border,ln=0)
        pdf.cell(20, row_height, f'{df["QTY"].iloc[i]}', 1, 0, 'C',fill=cell_filled)
        pdf.cell(105, row_height, f'{df["DESCRIPTION"].iloc[i]}', 1, 0, 'L',fill=cell_filled)
        pdf.cell(30, row_height, f'{str(df["UNIT PRICE"].iloc[i])}', 1, 0, 'R',fill=cell_filled)
        pdf.cell(last_column_width, row_height, f'{str(df["AMOUNT"].iloc[i])}', 1, 1, 'R',fill=cell_filled)
    
    # Subtotal
    pdf.cell(155,row_height+2,f'Subtotal',turn_on_border,0,'R')
    pdf.cell(last_column_width,row_height+2,f'{str(df["AMOUNT"].iloc[i])}',1,1,'R')
    
    # VAT
    pdf.cell(155,row_height+2,f'VAT 0.0%',turn_on_border,0,'R')
    pdf.cell(last_column_width,row_height+2,f'0.00',1,1,'R')
    
    # TOTAL
    pdf.set_font('arial', 'B', 15)
    pdf.cell(155,row_height+2,f'Total in GBP',turn_on_border,0,'R')
    pdf.set_fill_color(background_fill[0],background_fill[1],background_fill[2])
    pdf.cell(last_column_width,row_height+2,f' {str(df["AMOUNT"].iloc[i])}',1,1,'R',True)
    
    pdf.set_font('arial', 'B', 15)
    pdf.cell(155,row_height+2,f'Total in USD',turn_on_border,0,'R')
    pdf.set_fill_color(background_fill[0],background_fill[1],background_fill[2])
    pdf.cell(last_column_width,row_height+2,f'$ {usd_pay:,.2f}',1,1,'R',True)

    # -------------------------End Table-------------------------
    # Spacing
    pdf.cell(1,10,border=turn_on_border,ln=1)
    
    # Exchange rate
    pdf.set_font('arial', 'B', 11)
    pdf.cell(10,5,f'Using 1 GBP = {gbp_to_usd_rate} USD',turn_on_border,ln=2)
    pdf.set_font('arial', '', 11)
    pdf.cell(10,5,f"(Obtained from OANDA's monthly average rate from {start_date.strftime('%d')} - {end_date.strftime('%d %B, %Y')})",turn_on_border,ln=2)
    
    # Spacing
    pdf.cell(1,40,border=turn_on_border,ln=1)
    
    # Bank details
    pdf.set_font('arial', 'B', 15)
    pdf.cell(120,5,'PAYMENT DETAILS:',border=turn_on_border,ln=2)
    pdf.cell(120,3,'',border=turn_on_border,ln=2)
    pdf.set_font('arial', '', 12)
    pdf.cell(120,5,f"{employee_data['bank_name']}",border=turn_on_border,ln=2)
    pdf.cell(120,5,f"{employee_data['bank_address']}",border=turn_on_border,ln=2)
    pdf.cell(120,5,f"Holder: {employee_data['holder_name']}",border=turn_on_border,ln=2)
    pdf.cell(120,5,f"SWIFT code: {employee_data['swift']}",border=turn_on_border,ln=2)
    pdf.cell(120,5,f"Routing Nr.: {employee_data['routing_nb']}",border=turn_on_border,ln=2)
    pdf.cell(120,5,f"Account Nr.: {employee_data['account_nb']}",border=turn_on_border,ln=2)

    save_file_name = os.path.join(PROCESSED_DIRECTORY,f'{year}-{month}-{company_data["name"]}.pdf')
    pdf.output(save_file_name, 'F')
    
def generate_invoice(month,year,gbp_to_usd_rate,pay_rate,company_data={},employee_data={}):
    """
    Generate an invoice for given month and year based on the worked hours and pay rate, and save it as a PDF.

    Parameters:
    - month (int): Month for which the invoice is to be generated.
    - year (int): Year for which the invoice is to be generated.
    - gbp_to_usd_rate (float): The conversion rate from GBP (Great Britain Pound) to USD (US Dollar).
    - pay_rate (float): The rate of pay per hour in GBP.
    - company_data (dict, optional): Dictionary containing the billing company's details. At minimum, it should have the key:
        * name: Name of the company. This is used to extract work hours specific to the company.
    - employee_data (dict, optional): Dictionary containing the employee's details, passed to the PDF generation function.

    Outputs:
    - A PDF invoice saved in a predefined directory, generated using the generate_table_and_save_pdf function.

    Notes:
    - This function utilizes the extract_worked_hour_as_df function to get the total worked hours for the given company.
    - The function uses pandas for DataFrame operations.
    - Additional libraries/modules required: pandas (as pd).
    - The function assumes that generate_table_and_save_pdf is available and defined with the correct parameters.
    """
    _,total_hours = extract_worked_hour_as_df(month,year,company_data['name'])

    total_gbp = int(total_hours[:-3])*pay_rate

    total_usd = round(gbp_to_usd_rate*total_gbp,0)
    
    df = pd.DataFrame([[total_hours[:-3],'Work hours',u"\xA3 "+f'{pay_rate:.2f}',u"\xA3 "+f'{total_gbp:,.2f}']],columns=['QTY','DESCRIPTION','UNIT PRICE','AMOUNT'])
    generate_table_and_save_pdf(df,month,year,gbp_to_usd_rate,
                                usd_pay=total_usd,
                                company_data=company_data,
                                employee_data=employee_data)

def plot_weekly_hour_distribution(df):
    """
    Plot the distribution of work hours for each day of the week based on the input DataFrame.

    Parameters:
    - df (pandas.DataFrame): DataFrame containing work hour data. The DataFrame should have at least two columns:
        * Begin: Start time of the work, expected as a timestamp or datetime64.
        * End: End time of the work, expected as a timestamp or datetime64.

    Outputs:
    - A visual representation (plot) showcasing the distribution of work hours for each weekday.

    Notes:
    - The function assumes that matplotlib and numpy are imported respectively as plt and np.
    - The function utilizes global variables like DAYS for weekday labels and relies on helper functions like get_wk_nb.
    - The color coding of work hours is based on the week number of the month, and a legend is provided for clarity.
    - The function does not explicitly return the figure, but the plotted figure will be shown when using plt.show() in a script or interactive session.
    """
    fig = plt.figure(figsize=(18, 9))
    ax=fig.add_subplot(1, 1, 1)
    ax.set_title('Workweek', y=1, fontsize=18)

    ax.set_xlim(0.5, len(DAYS) + 0.5)
    ax.set_xticks(range(1, len(DAYS) + 1))
    ax.set_xticklabels(DAYS,fontsize=14)
    ax.grid(axis='y', linestyle='--', linewidth=0.5)
    ax.yaxis.set_major_locator(HourLocator())

    ax.yaxis.set_major_formatter(DateFormatter("%H:00"))

    start=df.Begin[0]-np.timedelta64(df.Begin[0].hour,'h')-np.timedelta64(df.Begin[0].minute,'m')
    end = start+np.timedelta64(24,'h')
    ax.set_ylim(start, end)
    width=0.48
    month = df.Begin[0].month
    for i in range(len(df)):
        day_shift= np.timedelta64((df.Begin[i]-start).days, 'D')
        ax.fill_between([1+df.Begin[i].weekday()-width,1+df.Begin[i].weekday()+width],
                        [df.Begin[i]-day_shift,
                         df.Begin[i]-day_shift],
                        [df.End[i]-day_shift,
                         df.End[i]-day_shift],
                        alpha=0.8,color=f'C{get_wk_nb(df.Begin[i])-month}')
    plt.gca().invert_yaxis()
    weeks_present = np.unique(df.Begin.apply(get_wk_nb))
    for ind,week_nb in enumerate(weeks_present):
        fig.text(0.15+ind*0.04, 0.9, f"Week {week_nb} ",backgroundcolor=f'C{week_nb-month}', color='white', weight='roman', size='medium')