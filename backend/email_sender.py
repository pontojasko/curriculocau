import os
import smtplib
from email.message import EmailMessage

def send_resume_email(to_email: str, subject: str, body: str, pdf_path: str) -> bool:
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    
    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        print("SMTP configurado incorretamente. Falta variáveis de ambiente.")
        return False
        
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg.set_content(body)
        
        # Attach PDF
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
            
        pdf_filename = os.path.basename(pdf_path)
        msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
        
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            # Note: starttls() may not be needed for some ports, but is common for 587/2525. 
            # We'll use starttls() as it's standard.
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False
