from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
from typing import List
import schemas as schema
import random
import models

class EmailSchema(BaseModel):
    email: EmailStr

conf = ConnectionConfig(
    MAIL_USERNAME="derciomichaque@gmail.com",
    MAIL_PASSWORD="drifoiylpnlxaiiy",  # Certifique-se de que está correto
    MAIL_FROM="derciomichaque@gmail.com",
    MAIL_FROM_NAME="Boleia Support",
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,  # STARTTLS usa a porta 587
    MAIL_STARTTLS=True,  # ✅ Ativar STARTTLS
    MAIL_SSL_TLS=False,  # ❌ Não use SSL/TLS ao mesmo tempo
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
#EmailConfirmation
def get_confirmation_email_by_id(db: Session, id: int):
    return db.query(models.EmailConfirmation).filter(models.EmailConfirmation.id == id).first()

def get_confirmation_email_by_user_id(db: Session, user_id: int):
    return db.query(models.EmailConfirmation).filter(models.EmailConfirmation.user_id == user_id).first()

#Get EmailConfirmation
def get_confirmation_email(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.EmailConfirmation).offset(skip).limit(limit).all()


#create EmailConfirmation
def create_confirmation_email(db: Session,user_id:int, confirmation_code: str):
    db_con_emai = models.EmailConfirmation(user_id=user_id, confirmation_code=confirmation_code)
    db.add(db_con_emai)
    db.commit()
    db.refresh(db_con_emai)
    return db_con_emai

def update_confirmation_email(db: Session, con_emai: schema.EmailConfirmationUpdate, con_emai_data: schema.EmailConfirmationRead):
    con_emai = con_emai.dict(exclude_unset=True)
    for key, value in con_emai.items():
            setattr(con_emai_data, key, value)
    db.add(con_emai_data)
    db.commit()
    db.refresh(con_emai_data)
    return con_emai_data


def delete_confirmation_email(db: Session, con_emai):
    if con_emai:
        db.delete(con_emai)
        db.commit()
        return True

async def generate_confirmation_code(db:Session, user_id: int, low: int = 100000, high: int= 999999):
    random_int = str(random.randint(low, high))
    hash_random_int = str(hash(random_int))
    confirmation_obj = create_confirmation_email(db, user_id, hash_random_int)
    saved_hashed_code = confirmation_obj.confirmation_code

    if saved_hashed_code:
        return saved_hashed_code, random_int
    else:
        raise HTTPException(status_code=404, detail="user not found")

def check_confirmation_code_match(db:Session, user_id: int, confirmation_code: int):
    confirmation_code = str(confirmation_code)
    hash_random_int = str(hash(confirmation_code))
    confirmation_obj = get_confirmation_email_by_user_id(db=db, user_id=user_id)
    confirmation_code_hashed = confirmation_obj.confirmation_code
    if confirmation_code_hashed == hash_random_int:
        return True, confirmation_obj
    else:
        return False, confirmation_obj


async def send_verification_email(email: EmailSchema, confirmation_code: int) -> JSONResponse:
    html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Confirmação de E-mail - Boleia</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background: #ffffff;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
                        text-align: center;
                    }}
                    .header {{
                        background: #007bff;
                        color: #ffffff;
                        padding: 15px;
                        font-size: 20px;
                        font-weight: bold;
                        border-top-left-radius: 8px;
                        border-top-right-radius: 8px;
                    }}
                    .content {{
                        padding: 20px;
                        font-size: 16px;
                        color: #333333;
                    }}
                    .code {{
                        display: inline-block;
                        font-size: 24px;
                        font-weight: bold;
                        color: #007bff;
                        background: #f8f9fa;
                        padding: 10px 20px;
                        border-radius: 5px;
                        margin: 10px 0;
                    }}
                    .footer {{
                        font-size: 12px;
                        color: #777777;
                        padding: 10px;
                        margin-top: 20px;
                        border-top: 1px solid #dddddd;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">Confirmação de E-mail - Boleia</div>
                    <div class="content">
                        <p>Olá,</p>
                        <p>Obrigado por se juntar à <strong>Boleia</strong>! Antes de começar a partilhar viagens, precisamos confirmar o seu e-mail.</p>
                        <p>Por favor, utilize o seguinte código para ativar a sua conta:</p>
                        <div class="code">{confirmation_code}</div>
                        <p>Se não solicitou este e-mail, pode ignorá-lo com segurança.</p>
                    </div>
                    <div class="footer">
                        © {2025} Boleia. Todos os direitos reservados.<br>
                        <a href="https://boleia.com" style="color: #007bff; text-decoration: none;">Visite o nosso site</a> | 
                        <a href="mailto:suporte.boleia@outlook.com" style="color: #007bff; text-decoration: none;">Contacte-nos</a>
                    </div>
                </div>
            </body>
            </html>
            """

    message = MessageSchema(
        subject="Fastapi-Mail module",
        recipients=[email],
        body=html,
        subtype=MessageType.html)

    fm = FastMail(conf)
    await fm.send_message(message)
    return True