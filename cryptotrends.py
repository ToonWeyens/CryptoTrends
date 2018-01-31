from lxml import html
import requests
import numpy as np
import tkinter
import matplotlib.pyplot as plt
import matplotlib.dates as md
import arrow
import datetime as dt
from pytrends.request import TrendReq
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

####################
# INPUT PARAMETERS #
####################
# start month and end month:
month_start = -3
month_end = -0

# currency
currency = 'bitcoin'
#currency = 'ethereum'
#currency = 'ripple'
#currency = 'cardano'
#currency = 'stellar'
#currency = 'raiblocks'
##################
####################

##################
# 1: PREPARATION #
##################

# for https://pythonprogramming.net/advanced-matplotlib-graphing-charting-tutorial/
def movingaverage(values,window):
    weigths = np.repeat(1.0, window)/window
    smas = np.convolve(values, weigths, 'valid')
    return smas

def ExpMovingAverage(values, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a

# set up auxiliary variables
date_fmt = []
date_fmt.append('YYYYMMDD')
date_fmt.append('YYYY-MM-DD')
utc = []
# index 0: format YYYYMMDD, for google trends
utc.append([])
utc[0].append(arrow.utcnow().shift(months=month_start).format(date_fmt[0]))
utc[0].append(arrow.utcnow().shift(months=month_end).format(date_fmt[0]))
# index 1: format YYYY-MM-DD, for google trends
utc.append([])
n_google_reqs = month_end-month_start
for i in range(0,n_google_reqs):
    utc[1].append([])
    utc[1][0].append(arrow.utcnow().shift(months=month_start+i).format(date_fmt[1]))
    utc[1].append([])
    utc[1][1].append(arrow.utcnow().shift(months=month_start+i+1).shift(days=-1).format(date_fmt[1]))

####################
# 2: COINMARKETCAP #
####################

# from http://python-docs.readthedocs.io/en/latest/scenarios/scrape.html
url = "https://coinmarketcap.com/currencies/"+currency+"/historical-data/?start="+utc[0][0]+"&end="+utc[0][1]
print('scraping coinmarketcap for "{}"'.format(currency))
page = requests.get(url)
tree = html.fromstring(page.content)

#<td class="text-left">Jan 23, 2018</td>
dates = tree.xpath('//td[@class="text-left"]/text()')
#<td data-format-fiat="" data-format-value="10944.5">10,944.50</td>
prices = tree.xpath('//td[@data-format-fiat=""]/text()')

n_days = []
n_days.append(len(dates))
dates_array = []
dates_array.append(np.zeros([n_days[0]]))
prices_array = []
prices_array.append(np.zeros([n_days[0],5]))
print("    number of days: {}".format(n_days[0]))
print('')

# from https://stackoverflow.com/a/43966667/3229162
def replace_month_abrev(date_string):
    month_dict = {"Jan ": "January ",
              "Feb ": "February ",
              "Mar ": "March ",
              "Apr ": "April ",
              "May ": "May ",
              "Jun ": "June ",
              "Jul ": "July ",
              "Aug ": "August ",
              "Sep ": "September ",
              "Sept ": "September ",
              "Oct ": "October ",
              "Nov ": "November ",
              "Dec ": "December "}
    # find all dates with abrev
    abrev_found = filter(lambda abrev_month: abrev_month in date_string, month_dict.keys())
    # replace each date with its abbreviation
    for abrev in abrev_found:
        date_string = date_string.replace(abrev, month_dict[abrev])
    # return the modified string (or original if no states were found)
    return date_string

# from https://stackoverflow.com/a/43426567/3229162
formats = ['MMMM Do YYYY', 'Do MMMM YYYY', 'MMM Do YYYY', 'MM/DD/YYYY', 'M D YYYY', 'MMMM D, YYYY', 'YYYY-MM-DD']
def convert_datetime(date):
    for format in formats:
        try:
            date = replace_month_abrev(date)
            #return arrow.get(date, format).format('MM/DD/YYYY')
            return arrow.get(date, format).format('X')
            break
        except (arrow.parser.ParserError, ValueError) as e:
            pass

i_tot = 0
#print("Day         :  open high low close average")
#print()
for i in range(0,n_days[0]):
    dates_array[0][i] = convert_datetime(dates[i])
    for j in range(0,4):
        prices_array[0][i,j] = prices[i_tot]
        i_tot += 1
    prices_array[0][i,4] = 0.5*sum(prices_array[0][i,1:3])
    #print("{}: {}".format(dates_array[0][i],prices_array[0][i,:]))

####################
# 3: GOOGLE TRENDS #
####################

# from https://github.com/GeneralMills/pytrends
print('searching google trends')
pytrends = TrendReq(hl='en-US', tz=360)
kw_list = ["buy "+currency]
#pytrends.build_payload(kw_list, cat=0, timeframe=utc[1][0]+' '+utc[1][1], geo='', gprop='')

print('    global search:')
print('        search timeframe: {}'.format(utc[1][0][0]+' -> '+utc[1][1][n_google_reqs-1]))
pytrends.build_payload(kw_list, cat=0, timeframe=utc[1][0][0]+' '+utc[1][1][n_google_reqs-1], geo='', gprop='')
google_interest_values = pytrends.interest_over_time()[kw_list[0]]
dates_tot = []
prices_tot = []
n_days.append(len(google_interest_values.index.format()))
for j in range(0,n_days[1]):
    dates_tot.append(convert_datetime(google_interest_values.index.format()[j]))
    prices_tot.append(google_interest_values.values[j])

dates_array.append(np.zeros([n_days[1]]))
prices_array.append(np.zeros([n_days[1]]))
for i in range(0,n_days[1]):
    dates_array[1][i] = float(dates_tot[i])
    prices_array[1][i] = float(prices_tot[i])


print('    finer searches:')
n_days.append(0)
n_days_loc = 0
dates_loc = []
prices_loc = []
for i in range(0,n_google_reqs):
    # use API
    print('        search timeframe: {}'.format(utc[1][0][i]+' -> '+utc[1][1][i]))
    pytrends.build_payload(kw_list, cat=0, timeframe=utc[1][0][i]+' '+utc[1][1][i], geo='', gprop='')
    google_interest_values = pytrends.interest_over_time()[kw_list[0]]
    n_days_loc = len(google_interest_values.index.format())
    n_days[2] += n_days_loc
    print("            number of days: {}".format(n_days_loc))
    for j in range(0,n_days_loc):
        dates_loc.append(convert_datetime(google_interest_values.index.format()[j]))
        prices_loc.append(float(google_interest_values.values[j]))
    
    # find max in global
    max_tot = 0
    for j in range(0,n_days[1]):
        #print('tot = {}, minmax = {}, {}'.format(dates_tot[j],dates_loc[n_days[2]-n_days_loc],dates_loc[n_days[2]-1]))
        if dates_tot[j] >= dates_loc[n_days[2]-n_days_loc] and dates_tot[j] <= dates_loc[n_days[2]-1]:
            max_tot = max(max_tot,prices_tot[j])
            #print(' => yes, max_tot = {}'.format(max_tot))
    
    # rescale
    for j in range(n_days[2]-n_days_loc,n_days[2]):
        prices_loc[j] *= float(max_tot)/100
    print('            local weight: {}'.format(float(max_tot)/100))


print("    number of days: {}".format(n_days[2]))
dates_array.append(np.zeros([n_days[2]]))
prices_array.append(np.zeros([n_days[2]]))
for i in range(0,n_days[2]):
    dates_array[2][i] = float(dates_loc[i])
    prices_array[2][i] = float(prices_loc[i])

################
# 4: ANALYTICS #
################

print('')
print('calculating EMA')

####################
# 5: VISUALIZATION #
####################

print('')
print('plotting')

max_prices = []
max_prices.append(prices_array[0][:,4].max())
max_prices.append(prices_array[1][:].max())
max_prices.append(prices_array[2][:].max())

# From https://stackoverflow.com/a/4091264/3229162
dates_dt = []
for i in range(0,3):
    dates_dt.append([dt.datetime.fromtimestamp(date) for date in dates_array[i]])

fig, ax = plt.subplots()
fig.set_size_inches(18.5, 10.5)
ax.set_ylim([0,100])
plt.xticks( rotation=25 )
plt.subplots_adjust(bottom=0.2)
xfmt = md.DateFormatter('%d-%m-%Y')
ax.xaxis.set_major_formatter(xfmt)
ax.plot(dates_dt[0],prices_array[0][:,4]/max_prices[0]*100,c='red',linewidth=3,label='price')
ax.fill_between(dates_dt[1],prices_array[1][:]/max_prices[1]*100,facecolor='blue',alpha=0.25,linestyle='dotted',label='g. trends rough "'+kw_list[0]+'"')
ax.plot(dates_dt[2],prices_array[2][:]/max_prices[2]*100,c='blue',linewidth=3,label='g. trends fine "'+kw_list[0]+'"')
plt.grid(True,linestyle='dotted')
plt.tight_layout()

now = arrow.utcnow().format('YYYY-MM-DD_HH:mm:ss')
leg = ax.legend(loc='upper center', shadow=True)
leg_lines = leg.get_lines()
leg_texts = leg.get_texts()
plt.setp(leg_lines, linewidth=4)
plt.setp(leg_texts, fontsize='x-large')
#plt.show()
filename = 'CryptoTrends_'+now+'.png'
plt.savefig(filename)
print('    Saved file in "{}"'.format(filename))

##################
# 5: SEND EMAIL  #
##################
# (from https://docs.python.org/3/library/email.examples.html)

print('')
print('sending email')

# set up email addresses
exec(open("./email_data").read())

# current date
now = arrow.utcnow().format('YYYY-MM-DD (HH:mm:ss UTC)')
subject = 'CryptoTrends '+now

# Create the container email message.
# (from https://docs.python.org/3.4/library/email-examples.html, third example, 31/01/2018)
msg = MIMEMultipart()
msg['Subject'] = subject
msg['From'] = notifier_email
msg['To'] = ', '.join(receiver_email)
msg.preamble = subject

with open(filename, 'rb') as fp:
    img_data = MIMEImage(fp.read())

msg.attach(img_data)

# Send the email via Gmail
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login(notifier_email, password)
s.send_message(msg)
s.quit()

print('    Sent image to')
for i in range(0,len(receiver_email)):
    print('        '+receiver_email[i])
