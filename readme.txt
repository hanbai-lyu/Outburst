outburst.py

When directly run as a script, it gets the SWIFT and MAXI data from the web service, does the photon count analysis, generate a pdf report in the run directory, and send an alert if any possible outburst occurs.

When imported as a module (import outburst), it has 3 useful methods:

outburst.get(tolerance=0.2, save=True)
get the SWIFT and MAXI data. Tolerance (default 0.2) means the tolerated difference in swift and maxi degs for two sources to be considered the same. If save is set to True (default), the results are saved as combined.xlsx, swift.txt, and maxi.txt in folder 'output' under the run directory. If save is set to False, the function returns a dataframe containing all parsed information. Use keys 'Swift Link' and 'Maxi Link' to access links as an iterable series.

outburst.report(filename='summary_light_curves.pdf')
generate a pdf file under the run directory with the input name containing all parsed light curves. Returns a boolean flag that is True if any light curve indicates an outburst and False otherwise.

outburst.alert(filename='summary_light_curves.pdf', to=['guglielmo.mastroserio@inaf.it'])
send an alert email attaching the specified file to the given email addresses. The email is sent from a gmail account hl.outburstalert@gmail.com.

Dependencies: you need to install packages beautifulsoup4 and tqdm (both available via pip)