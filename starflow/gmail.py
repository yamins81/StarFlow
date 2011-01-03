#!/usr/bin/env python
'''
	Contains functions for sending emails via gmail api. 
'''

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

def Gmail(account,password,to,subject='',Text = None, FileName = None):	
	'''
		Sends an email from specified Gmail account to specified recipient address, 
		with subject and body from specified text or from text in specified file.
		 
		Account = string :  Gmail account name, e.g. if your gmail address was 
		"dyamins@gmail.com", 
			then account would be set to "dyamins"
		password = string: password for the above specified account.
		
		To = email address to which the email will be send, e.g. 
		"info@barackobama.com"
		
		Subject = string to be used as subject field of email, e.g. "Let's meet 
		Thursday"
		
		Text = string : text to be used as body of email 
		
		FileName  = pathname string : if Text not specified, the contents of the file 
		FileName are read in and used as the body.
		--> Either Text or FileName must be specified (if both, Text is used 
		preferentially.)
		
		returns : nothing.  (but prints a status message after message is sent or 
		fails.)
	'''

	if isinstance(to,str):
		to = to.split(',')
	
	msg = MIMEMultipart()
	msg['From'] = account + '@gmail.com'
	msg['To'] = ', '.join(to)
	msg['Subject'] = subject
	
	
	mailServer = smtplib.SMTP('smtp.gmail.com',587)
	mailServer.ehlo()
	mailServer.starttls()
	mailServer.ehlo()
	mailServer.login(msg['From'],password)

	if Text == None:
		assert FileName != None, 'FileName or Text must be specified'
		Text = open(FileName,'r').read()
	msg.attach(MIMEText(Text))	
	
	
	X = mailServer.sendmail(msg['From'],to,msg.as_string())
	if X != {}:
		print "...message(s) to", msg['To'], "failed"
	else:
		print  "...message(s) to", msg['To'], "sent."
			
	mailServer.close()
