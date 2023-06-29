# -*- coding: utf-8 -*-

# Import libraries
import os
import requests
import pandas as pd
import numpy as np
import smtplib
import ssl
import urllib.request
import matplotlib.pyplot as plt
from email.message import EmailMessage
from bs4 import BeautifulSoup
from tqdm import tqdm
from astropy.time import Time
import warnings
warnings.filterwarnings("ignore")


def alert(filename='summary_light_curves.pdf', to=['guglielmo.mastroserio@inaf.it']):
    gmail_user = 'hl.outburstalert@gmail.com'
    gmail_password = 'hnewjchcpitgndgx'
    context = ssl.create_default_context()
    
    msg = EmailMessage()
    msg["From"] = gmail_user
    msg["Subject"] = 'Possible outbursts'
    msg["To"] = to
    msg.set_content('Diagrams with possible alerts marked in colors have been attached.')
    
    with open(filename, 'rb') as content_file:
        content = content_file.read()
        msg.add_attachment(content, maintype='application', subtype='pdf', filename=filename)
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.close()
    
        print('Email sent!')
    except Exception as e:
        print(e)


def swf_scraper(url):
    # Create object page
    page = requests.get(url)

    # Obtain page's information
    soup = BeautifulSoup(page.text, 'lxml')

    # Obtain information from tag <table>
    table1 = soup.find('table', class_='styled-table')

    # Obtain every title of columns with tag <th>
    headers = ['Swift Link']
    for i in table1.find_all('th'):
        title = i.text
        headers.append(title)

    # Create a dataframe
    mydata = pd.DataFrame(columns=headers)

    # Create a for loop to fill mydata
    for j in table1.find_all('tr')[1:]:
        row_file = url + j.find('a', href=True)['href'] + '.lc.txt'
        row_data = j.find_all('td')
        row = [i.text for i in row_data]
        row.insert(0, row_file)
        length = len(mydata)
        mydata.loc[length] = row

    return mydata


def maxi_scraper(url):
    link_head = 'http://maxi.riken.jp'

    # Create object page
    page = requests.get(url)

    # Obtain page's information
    soup = BeautifulSoup(page.text, 'lxml')

    # Obtain information from tag <table>
    table1 = soup.find('table')

    # Obtain every title of columns
    i = table1.find('tr')
    row_data = i.find_all('td')
    headers = [j.text for j in row_data]
    headers.insert(0, 'Maxi Link')

    # Create a dataframe
    mydata = pd.DataFrame(columns=headers)

    # Create a for loop to fill mydata
    for j in table1.find_all('tr')[1:]:
        row_file = link_head + j.find('a', href=True)['href'][2:-5] + '_g_lc_1day_all.dat'
        row_data = j.find_all('td')
        row = [i.text for i in row_data]
        row.insert(0, row_file)
        length = len(mydata)
        mydata.loc[length] = row

    return mydata


def get(tolerance=0.2, save=True):
    
    degs = ['RA J2000 Degs', 'Dec J2000 Degs']
    degs_approx = ['RA J2000 Degs_app', 'Dec J2000 Degs_app']
    df_swf = swf_scraper('https://swift.gsfc.nasa.gov/results/transients/')
    df_swf['Source Type'] = df_swf['Source Type'].str.rstrip()
    
    swf1 = df_swf[df_swf['Source Type'].str.contains('BH')]
    swf2 = df_swf[df_swf['Source Type'].isin(['LMXB', 'XRB', 'X-ray source'])]
    swift_data = pd.concat([swf1, swf2])
    swift_data = swift_data[['Swift Link', 'Source Name', 'Source Type', 'RA J2000 Degs', 'Dec J2000 Degs']]
    
    df_maxi = maxi_scraper('http://maxi.riken.jp/top/slist_ra.html')
    df_maxi[degs] = df_maxi['R.A., Dec'].str.split(', ', expand=True)
    df_maxi.rename(columns={'source name': 'Source Name Maxi'}, inplace=True)
    maxi_data = df_maxi[['Maxi Link', 'Source Name Maxi', 'RA J2000 Degs', 'Dec J2000 Degs']]

    swift_data.loc[:, degs] = swift_data[degs].astype(float).round(2)
    maxi_data.loc[:, degs] = maxi_data[degs].astype(float).round(2)
    
    swift_data[degs_approx] = (swift_data[degs] / tolerance).round().astype(int)
    maxi_data[degs_approx] = (maxi_data[degs] / tolerance).round().astype(int)
    df_comb = swift_data.merge(maxi_data, on=degs_approx, how='left', suffixes=('_swf', '_maxi'))
    
    if save:
        os.makedirs('output', exist_ok=True)
        with pd.ExcelWriter('output/combined.xlsx') as writer:  
            swift_data.drop(columns=degs_approx).to_excel(writer, sheet_name='swift', index=False)
            maxi_data.drop(columns=degs_approx).to_excel(writer, sheet_name='maxi', index=False)
            df_comb.drop(columns=degs_approx).to_excel(writer, sheet_name='combined', index=False)
        
        np.savetxt('output/swift.txt', df_comb['Swift Link'].values, fmt='%s')
        np.savetxt('output/maxi.txt', df_comb['Maxi Link'].values, fmt='%s')
    else:
        return df_comb


def report(filename='summary_light_curves.pdf'):
    outburst = False
    df = get(save=False)
    sources_BAT = df['Swift Link'].values
    sources_maxi = df['Maxi Link'].values
    
    fig = plt.figure(figsize=(15, len(sources_BAT)*3))

    ax = []
    
    maxi_col = 'blue'
    BAT_col = 'k'
    
    num_last_rate = 5 #number of days to calculate the average 
    threshold_rate_BAT = 0.001
    threshold_rate_maxi = 0.001
    back_days = 20
    today = Time.now().mjd
    
    for j, name in enumerate(tqdm(sources_BAT)):
    
    # BAT open file 
        fp = urllib.request.urlopen(name)
        mybytes = fp.read()
    
        mystr = mybytes.decode("utf8")
        fp.close()
        lenght_file = len(mystr.split('\n')) 
    
        day_BAT = []
        rate_BAT = []
        err_rate_BAT = []    
        
        for i,line in enumerate(mystr.split('\n')):
        # print(i)
            if ( i > 5 and i < lenght_file - 1): 
                day_BAT.append(float(line.split()[0]))
                rate_BAT.append(float(line.split()[1]))
                err_rate_BAT.append(float(line.split()[2]))
    
        ax.append(fig.add_subplot(len(sources_BAT) + 1, 1, j + 1))
    
        #Figure out the source name 
        source_name = name.split('/')[-1].split('.')[0]
    
        #Plot BAT
        ax[j].errorbar(day_BAT, rate_BAT, yerr=err_rate_BAT, marker='+', ls='none',
                       color=BAT_col, label= 'Swift/BAT: ' + source_name)
        ax[j].hlines(y=0.0, xmin=0, xmax=day_BAT[-1] + 3, linewidth=0.5, color=BAT_col)
        ax[j].set_xlim( day_BAT[-1] - back_days, day_BAT[-1] + 3)
    
        ax[j].set_xlabel(r'Time [MJD]', fontsize = 20, color=BAT_col)
        ax[j].set_ylabel(r'Counts/cm$^2$/s ', fontsize = 20, color=BAT_col)
        ax[j].tick_params(which='major', width=2,length=15,labelsize=20, pad=10, color=BAT_col)
        ax[j].tick_params(which='minor', width=2,length=8,labelsize=20, pad=10, color=BAT_col)
        for axis in ['top','bottom','left','right']:
            ax[j].spines[axis].set_linewidth(3)
        ax[j].tick_params('y', colors=BAT_col)
        ax[j].set_ylim(-0.05, 0.05)
    
        ax[j].legend(loc=(0.1, 0.1), title=r'',ncol=1 ,fontsize='20')
        ax[j].get_legend().get_title().set_fontsize('15') 
        last_day_BAT = Time(day_BAT[-1], format='mjd')
        ave_last_rate_BAT = 0.0
        if (today - last_day_BAT.mjd < 5 ): 
            
        #calculate the average rate of the last days (they are set by num_last_rate), \
        # only if rate is not compatible with zero accounting for the errors
            for day, rate_check, err_check in zip(day_BAT[-num_last_rate:], rate_BAT[-num_last_rate:],
                                                  err_rate_BAT[-num_last_rate:]):
                if ((today - day) < 5):
                    if ((rate_check - err_check) < 0.001):
                        ave_last_rate_BAT += 0.0 
                    else:
                        ave_last_rate_BAT += rate_check
                ave_last_rate_BAT /= num_last_rate
            
        #color the background in red if the rate of the last 3 days is higher than threshold_rate 
        if (ave_last_rate_BAT > threshold_rate_BAT):
            ax[j].set_facecolor('red')
            outburst = True
        
        day_BAT.clear()
        rate_BAT.clear()
        err_rate_BAT.clear()
    
        if pd.notna(sources_maxi[j]):
        # MAXI open file
            fp_maxi = urllib.request.urlopen(sources_maxi[j])
            mybytes_maxi = fp_maxi.read()
    
            mystr_maxi = mybytes_maxi.decode("utf8")
            fp_maxi.close()
            lenght_file = len(mystr_maxi.split('\n')) 
    
    
            day_maxi = []
            rate_maxi = []
            err_rate_maxi = []
    
    
            for i,line in enumerate(mystr_maxi.split('\n')[:-1]):
                day_maxi.append(float(line.split()[0]))
                rate_maxi.append(float(line.split()[1]))
                err_rate_maxi.append(float(line.split()[2]))
    
    
            # MAXI twin PLOT
            ax2 = ax[j].twinx()
            ax2.errorbar(day_maxi, rate_maxi, yerr=err_rate_maxi,
                         marker='+', ls='none', color=maxi_col, label= 'MAXI')
    
            ax2.set_ylim(-0.1, 0.1)
            ax2.tick_params(which='major', width=3,length=15,labelsize=20,pad=10,color=maxi_col)
            ax2.tick_params(which='minor', width=3,length=8,labelsize=20,pad=10,color=maxi_col)
            ax2.tick_params('y', colors=maxi_col)
            ax2.set_ylabel(r'Photons/cm$^2$/s',fontsize=20,color=maxi_col)

            last_day_maxi = Time(day_maxi[-1], format='mjd')
    
            #calculate the average rate of the last days (they are set by num_last_rate), \
            # only if rate is not compatible with zero accounting for the errors
            ave_last_rate_maxi = 0.0
            if (today - last_day_maxi.mjd < 5 ): 
    
                for day, rate_check, err_check in zip(day_maxi[-num_last_rate:], rate_maxi[-num_last_rate:],
                                                      err_rate_maxi[-num_last_rate:]):
                    if ((today - day) < 5):
                        if ((rate_check - err_check) < 0.01):
                            ave_last_rate_maxi = ave_last_rate_maxi + 0.0 
                        else:
                            ave_last_rate_maxi = ave_last_rate_maxi + rate_check
                ave_last_rate_maxi = ave_last_rate_maxi / num_last_rate
    
            if (ave_last_rate_maxi > threshold_rate_maxi):
                ax[j].set_facecolor('yellow')
                outburst = True
    
            day_maxi.clear()
            rate_maxi.clear()
            err_rate_maxi.clear()
    
    plt.savefig(filename, format='pdf', bbox_inches='tight')
    return outburst


if __name__ == '__main__':
    flag = report()
    if flag:
        alert()
