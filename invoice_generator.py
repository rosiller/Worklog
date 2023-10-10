from utils.invoice_utils import generate_invoice

company_data = {'name':'CompanyName',
                'street':'Building Street',
                'street_cont':'123 Street',
                'city':'Company city',
                'postcode':'12345'}

employee_data = {'name':"My Name",
                 'initials': "MyInitials",
                 'position':"My position",
                 'email':"myemail@company.com",
                 # Address:
                 'street':"My Street 123",
                 'city':"MyCity",
                 'state':"MyState",
                 'postcode':"12345",
                 'country':"My Country",
                 'phone':"+123 456 789",
                 # Bank details:
                 'bank_name':"My Bank",
                 'bank_address':"1234 Bank Street, Bank State, Country, Zip code",
                 'holder_name':"Holder Name",
                 'swift':"ABCDEF12",
                 'routing_nb':"123456789",
                 'account_nb':'12345679012'}


month = 6
year = 2022
gbp_to_usd_rate=1.232204 # https://www.oanda.com/lang/es/fx-for-business/historical-rates
hourly_rate = 1 # In GBP 

generate_invoice(month,year,gbp_to_usd_rate,hourly_rate,company_data,employee_data)