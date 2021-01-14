import smtplib

server = smtplib.SMTP('smtp.gmail.com', 587)

server.starttls()
server.login('senders address', 'password')
server.sendmail('senders address', 
                'receivers address',
                'Gotcha!!!')